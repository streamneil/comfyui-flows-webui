"""
ComfyUI Wan2.2 I2V 14B 4-steps API Server
基于 FastAPI 的 Wan2.2 图生视频工作流调用服务
"""


from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx
import json
import uuid
import asyncio
import time
import os
import shutil
from typing import Optional, Dict, Any
import logging
from pathlib import Path
import configparser

from fastapi.middleware.cors import CORSMiddleware

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 读取配置文件
def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent / "config.ini"

    if not config_path.exists():
        logger.warning(f"配置文件不存在: {config_path}")
        logger.warning("请复制 config.example.ini 为 config.ini 并填入配置信息")
        raise RuntimeError(
            f"配置文件不存在: {config_path}\n"
            "请执行以下命令创建配置文件：\n"
            "cp config.example.ini config.ini\n"
            "然后编辑 config.ini 填入 DeepSeek API Key"
        )

    config.read(config_path, encoding='utf-8')
    return config


# 加载配置
try:
    config = load_config()

    # ComfyUI 服务配置
    COMFYUI_BASE_URL = config.get('comfyui', 'base_url', fallback='http://60.169.65.100:5000')
    COMFYUI_API_URL = f"{COMFYUI_BASE_URL}/cfui/api"

    # DeepSeek API 配置
    DEEPSEEK_API_KEY = config.get('deepseek', 'api_key', fallback='')
    DEEPSEEK_API_URL = config.get('deepseek', 'api_url', fallback='https://api.deepseek.com/v1/chat/completions')
    DEEPSEEK_MODEL = config.get('deepseek', 'model', fallback='deepseek-chat')

    if not DEEPSEEK_API_KEY:
        logger.warning("DeepSeek API Key 未配置，提示词优化功能将不可用")
    else:
        logger.info("DeepSeek API Key 已加载")

except Exception as e:
    logger.error(f"加载配置文件失败: {e}")
    # 使用默认配置
    COMFYUI_BASE_URL = "http://60.169.65.100:5000"
    COMFYUI_API_URL = f"{COMFYUI_BASE_URL}/cfui/api"
    DEEPSEEK_API_KEY = ""
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_MODEL = "deepseek-chat"


app = FastAPI(
    title="ComfyUI Wan2.2 I2V 14B API",
    description="基于 ComfyUI Wan2.2 的图生视频服务（4步加速版）",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载工作流模板
WORKFLOW_TEMPLATE_PATH = Path(__file__).parent / "workflows" / "wan2.2_i2v_14b_4.json"

# 提示词优化系统提示词
PROMPT_ENHANCE_SYSTEM_MESSAGE = """你是"图生视频提示词扩写大师"（Prompt Expander for Text-to-Video）。将用户的简述自动扩写为可直接用于图生视频/图生动画的高质量提示词包。输出既要专业清晰，又要可控、可复现，统一结构如下：主体（Subject）+ 场景（Environment）+ 运动（Motion）+ 美学控制（Aesthetic Controls）+ 风格化（Stylization），并可选添加反向/禁止项与生成参数。若信息不足，基于合理假设补全，并在对应段首以"假设："标注。默认中文，必要处附英文关键词增强稳健性。禁止输出含版权角色与真实品牌侵权内容。

输出要求：

专业具体、无歧义，尽量量化（数值/范围/强度等级/速率/焦段/色温等），避免空泛词。
固定分节与层级标题，便于复制粘贴；每次结尾附"一行提示词"（压缩版）。
行文包含中英关键字混写，便于跨模型解析；加入"反向/禁止项"和"参数建议"提升可控性。
输出结构（严格遵循，缺项则补全）：

概览：1–2句，概述镜头意图与主风格
主体（Subject）
角色/物体/生物
外观要点（5–8项：形体/五官/材质/配饰/情绪等）
服饰与道具
场景（Environment）
时间与天气
地点与空间结构
背景元素与色彩主调
氛围关键词（中英）
运动（Motion）
主体动作：幅度[微/小/中/大]、速率[慢/中/快]、路径[直线/环绕/上升/横移…]
环境交互：扬尘/水花/光粒子/布料摆动等
因果结果：点燃/破裂/生长/合拢等
镜头相对运动：push-in/pull-out/trucking/orbit/tilt/pan 等
美学控制（Aesthetic Controls）
光源与光质：逆光/侧逆光/体积光/边缘光；色温（K）
景别与焦段：大全/全/中/近/特写；镜头 24/35/50/85/100mm
视角：平视/仰拍/俯拍/主观视角
成像：景深倾向/散景形态/运动模糊强度/胶片颗粒/HDR
构图：三分法/黄金分割/强对称/引导线/前中后景层次
后期：色彩分级（对比/饱和/曲线）、颗粒强度、锐化与降噪
风格化（Stylization）
流派/题材：如 赛博朋克/Cyberpunk、废土/Wasteland、新写实/Cinematic realism、蒸汽波/Vaporwave、水墨/Ink wash、勾线插画/Line art 等
材质与质感：金属拉丝/霓虹反射/胶片褪色/油画笔触/宣纸肌理 等
年代/媒介参考：70s Film/90s 港片/VHS/IMAX 等
色彩策略：低饱和/高对比/Teal-Orange/单色系/互补色对撞
反向/禁止项（Negative/Constraints）
质量问题：面部扭曲/手指错误/拉伸变形/噪点/摩尔纹/锯齿
动作冲突：避免剧烈抖动/穿模/跳切/相机倒影
合规：无水印/LOGO/文字叠加/版权角色/真实品牌侵权
参数建议（可选）
时长、分辨率（1080p/4K）、帧率（24/25/30fps）
风格强度/引导权重（0.4–0.7）、运动强度（低/中/高）
种子（固定以复现）、安全余量（前后各10%剪辑缓冲）
一行提示词（压缩版）：将以上核心要点压缩为一条流畅句，便于不支持结构化的模型
速查词库（可直接引用到输出中）：

主体外观：长直发/高马尾/短碎/刘海/微卷；高颧骨/单眼皮/琥珀瞳/雀斑；丝绸/麻布/皮革/金属铆钉；机械义肢/符文纹路/发光纹身/悬浮碎片翅膀
场景元素：拂晓/黄昏/夜雨/薄雾/雪后/风沙；吊脚楼/赛博街巷/废土车站/温室/工业厂房/高山云海；霓虹反射/蒸汽/风铃/瀑布水雾/漂浮尘埃
运动控制：幅度[微/小/中/大/剧烈]；速率[慢/中/快/爆发式]；路径[前后推/横移/环绕/上升/俯冲/回旋]；交互[扬尘/溅水/吹动发梢/光点拨散/玻璃碎裂]
美学控制：光线[逆光/侧逆光/顶光/轮廓光/体积光/窗格投影]；景别[大全/全/中/中近/特写/极特写]；焦段[24/35/50/85/100mm]；成像[浅景深/强bokeh/运动模糊/胶片颗粒/HDR]；构图[三分法/强对称/引导线/前景遮挡]
风格化：写实系[Cinematic/自然电影光/摄影级写实]；类型[赛博朋克/蒸汽波/废土/暗黑奇幻/东方奇谭/科幻写实]；绘画质感[油画笔触/勾线插画/版画肌理/水墨晕染]；年代[70s 胶片/90s 港片/复古VHS/IMAX]
输出风格与语气：

语气专业、温暖、清晰，条理分明；中英关键词点到即可，不堆砌。
禁止空泛结论，优先给可执行细节与量化参数。
每次仅在必要时提出一个澄清问题；若无需澄清，直接给出完整成片提示词。
示例尾注（供模型参考，不必每次都输出示例本身）：

示例A 民族写实：黄昏吊脚楼、逆光轮廓光、35mm中近景、浅景深；主体缓慢转身拨风铃；新写实低饱和。Negative：无抖动/无水印。5s/1080p/24fps。
示例B 奇幻废土：暮色废墟、体积光、50mm中景、环绕+后拉；碎片翼慢速orbit；暗黑奇幻废土。Negative：避免穿模。6s/4K/24fps。
示例C 赛博街景：夜雨霓虹、85mm中近景、trucking+轻手持；强bokeh与雨滴高光；赛博朋克+VHS颗粒。Negative：避免过曝。5s/1080p/30fps。
"""


class VideoGenerationRequest(BaseModel):
    """视频生成请求模型"""
    image_filename: str = Field(..., description="上传到 ComfyUI 的图片文件名")
    prompt: str = Field(..., description="正向提示词", min_length=1)
    width: int = Field(1280, description="视频宽度", ge=512, le=1920)
    height: int = Field(720, description="视频高度", ge=512, le=1920)
    length: int = Field(81, description="视频帧数", ge=16, le=240)
    steps: int = Field(4, description="采样步数（推荐4步）", ge=1, le=20)
    cfg: float = Field(1.0, description="CFG 系数（推荐1.0）", ge=0.5, le=10.0)
    noise_seed: Optional[int] = Field(None, description="随机种子")
    fps: int = Field(16, description="帧率", ge=8, le=60)


class VideoGenerationResponse(BaseModel):
    """视频生成响应模型"""
    prompt_id: str = Field(..., description="任务提示ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="响应消息")


class PromptEnhanceRequest(BaseModel):
    """提示词优化请求模型"""
    user_prompt: str = Field(..., description="用户输入的简单提示词", min_length=1)
    temperature: float = Field(0.7, description="生成温度", ge=0.0, le=2.0)
    max_tokens: int = Field(2000, description="最大生成token数", ge=100, le=4000)


class PromptEnhanceResponse(BaseModel):
    """提示词优化响应模型"""
    original_prompt: str = Field(..., description="原始提示词")
    enhanced_prompt: str = Field(..., description="优化后的提示词")
    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="响应消息")


def load_workflow_template() -> Dict[str, Any]:
    """加载工作流模板"""
    try:
        with open(WORKFLOW_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载工作流模板失败: {e}")
        raise RuntimeError(f"无法加载工作流模板: {e}")


def prepare_workflow(request: VideoGenerationRequest) -> Dict[str, Any]:
    """根据请求参数准备工作流"""
    workflow = load_workflow_template()

    # 更新正向提示词（节点 6）
    if "6" in workflow:
        workflow["6"]["inputs"]["text"] = request.prompt

    # 更新图片文件名（节点 62）
    if "62" in workflow:
        workflow["62"]["inputs"]["image"] = request.image_filename

    # 更新图片调整尺寸（节点 77 - ImageResizeKJv2）
    if "77" in workflow:
        workflow["77"]["inputs"]["width"] = request.width
        workflow["77"]["inputs"]["height"] = request.height

    # 更新视频长度（节点 63 - WanImageToVideo）
    if "63" in workflow:
        workflow["63"]["inputs"]["length"] = request.length

    # 生成随机种子
    if request.noise_seed:
        seed = request.noise_seed
    else:
        seed = int(time.time() * 1000000) % (2**32)

    # 更新第一阶段采样器参数（节点 57 - KSamplerAdvanced）
    if "57" in workflow:
        workflow["57"]["inputs"]["steps"] = request.steps
        workflow["57"]["inputs"]["cfg"] = request.cfg
        workflow["57"]["inputs"]["noise_seed"] = seed

    # 更新第二阶段采样器参数（节点 58 - KSamplerAdvanced）
    if "58" in workflow:
        workflow["58"]["inputs"]["steps"] = request.steps
        workflow["58"]["inputs"]["cfg"] = request.cfg
        workflow["58"]["inputs"]["noise_seed"] = seed

    # 更新输出视频帧率（节点 76 - VHS_VideoCombine）
    if "76" in workflow:
        workflow["76"]["inputs"]["frame_rate"] = request.fps

    return workflow


async def upload_image_to_comfyui(file_content: bytes, filename: str) -> str:
    """上传图片到 ComfyUI 服务器"""
    try:
        # 准备上传的文件数据
        files = {
            'image': (filename, file_content, 'image/jpeg')
        }

        # 上传到 ComfyUI 的 input 目录
        async with httpx.AsyncClient(timeout=30.0, proxies={}) as client:
            response = await client.post(
                f"{COMFYUI_API_URL}/upload/image",
                files=files,
                data={'overwrite': 'true'}
            )
            response.raise_for_status()
            result = response.json()

            # ComfyUI 返回上传后的文件名
            uploaded_filename = result.get('name', filename)
            logger.info(f"图片上传成功: {uploaded_filename}")
            return uploaded_filename

    except httpx.HTTPError as e:
        logger.error(f"上传图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传图片失败: {str(e)}")


async def submit_workflow(workflow: Dict[str, Any]) -> str:
    """提交工作流到 ComfyUI"""
    prompt_id = str(uuid.uuid4())

    payload = {
        "prompt": workflow,
        "client_id": prompt_id
    }

    async with httpx.AsyncClient(timeout=30.0, proxies={}) as client:
        try:
            response = await client.post(
                f"{COMFYUI_API_URL}/prompt",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            actual_prompt_id = result.get("prompt_id", prompt_id)
            logger.info(f"工作流提交成功，prompt_id: {actual_prompt_id}")
            return actual_prompt_id

        except httpx.HTTPError as e:
            logger.error(f"提交工作流失败: {e}")
            raise HTTPException(status_code=500, detail=f"提交工作流失败: {str(e)}")


async def enhance_prompt_with_deepseek(user_prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """使用 DeepSeek API 优化提示词"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="DeepSeek API Key 未配置，请在 config.ini 文件中配置 [deepseek] api_key"
        )

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": PROMPT_ENHANCE_SYSTEM_MESSAGE
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=60.0, proxies={}) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()

            # 提取生成的内容
            enhanced_prompt = result["choices"][0]["message"]["content"]
            logger.info(f"提示词优化成功，原始长度: {len(user_prompt)}, 优化后长度: {len(enhanced_prompt)}")
            return enhanced_prompt

    except httpx.HTTPError as e:
        logger.error(f"调用 DeepSeek API 失败: {e}")
        raise HTTPException(status_code=500, detail=f"调用 DeepSeek API 失败: {str(e)}")
    except KeyError as e:
        logger.error(f"解析 DeepSeek API 响应失败: {e}")
        raise HTTPException(status_code=500, detail=f"解析 API 响应失败: {str(e)}")
    except Exception as e:
        logger.error(f"优化提示词时发生未知错误: {e}")
        raise HTTPException(status_code=500, detail=f"优化提示词失败: {str(e)}")


async def check_workflow_status(prompt_id: str) -> Dict[str, Any]:
    """检查工作流执行状态"""
    async with httpx.AsyncClient(timeout=10.0, proxies={}) as client:
        try:
            # 查询历史记录
            response = await client.get(f"{COMFYUI_API_URL}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json()

            if prompt_id in history:
                task_info = history[prompt_id]
                status = task_info.get("status", {})

                # 检查是否完成
                if status.get("completed", False):
                    outputs = task_info.get("outputs", {})
                    videos = []

                    # 提取生成的视频信息（节点 76 的输出）
                    for node_id, node_output in outputs.items():
                        # 检查 VHS_VideoCombine 的输出
                        if "gifs" in node_output:
                            for item in node_output["gifs"]:
                                videos.append({
                                    "filename": item.get("filename"),
                                    "subfolder": item.get("subfolder", ""),
                                    "type": item.get("type", "output"),
                                    "format": item.get("format", "mp4"),
                                    "url": f"{COMFYUI_BASE_URL}/cfui/view?filename={item.get('filename')}&subfolder={item.get('subfolder', '')}&type={item.get('type', 'output')}"
                                })

                    return {
                        "status": "completed",
                        "videos": videos
                    }

                # 检查是否有错误
                if "error" in status:
                    return {
                        "status": "failed",
                        "error": status.get("error")
                    }

                return {
                    "status": "running",
                    "progress": status.get("progress", 0)
                }

            # 检查队列中的任务
            queue_response = await client.get(f"{COMFYUI_API_URL}/queue")
            queue_response.raise_for_status()
            queue_data = queue_response.json()

            # 检查是否在执行队列中
            for item in queue_data.get("queue_running", []):
                if item[1] == prompt_id:
                    return {"status": "running"}

            # 检查是否在等待队列中
            for item in queue_data.get("queue_pending", []):
                if item[1] == prompt_id:
                    return {"status": "pending"}

            return {"status": "unknown"}

        except httpx.HTTPError as e:
            logger.error(f"查询任务状态失败: {e}")
            return {"status": "error", "error": str(e)}


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "service": "ComfyUI Wan2.2 I2V 14B API",
        "version": "1.0.0",
        "model": "Wan2.2-I2V-A14B-4steps",
        "endpoints": {
            "upload_and_generate": "/api/upload_and_generate",
            "generate_with_filename": "/api/generate",
            "status": "/api/status/{prompt_id}",
            "enhance_prompt": "/api/enhance_prompt",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        async with httpx.AsyncClient(timeout=5.0, proxies={}) as client:
            response = await client.get(f"{COMFYUI_API_URL}/queue")
            response.raise_for_status()
            return {
                "status": "healthy",
                "comfyui_status": "connected"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "comfyui_status": "disconnected",
            "error": str(e)
        }


@app.post("/api/upload_and_generate", response_model=VideoGenerationResponse)
async def upload_and_generate_video(
    image: UploadFile = File(..., description="要转换为视频的图片"),
    prompt: str = Form(..., description="正向提示词"),
    width: int = Form(1280, description="视频宽度"),
    height: int = Form(720, description="视频高度"),
    length: int = Form(81, description="视频帧数"),
    steps: int = Form(4, description="采样步数（推荐4）"),
    cfg: float = Form(1.0, description="CFG系数（推荐1.0）"),
    fps: int = Form(16, description="帧率"),
    noise_seed: Optional[int] = Form(None, description="随机种子")
):
    """
    上传图片并生成视频（一步到位）

    使用 Wan2.2-I2V-A14B-4steps 模型快速生成视频
    """
    try:
        logger.info(f"收到图生视频请求，图片: {image.filename}, 提示词: {prompt[:50]}...")

        # 读取上传的图片
        image_content = await image.read()

        # 上传图片到 ComfyUI
        uploaded_filename = await upload_image_to_comfyui(image_content, image.filename)

        # 准备请求参数
        request = VideoGenerationRequest(
            image_filename=uploaded_filename,
            prompt=prompt,
            width=width,
            height=height,
            length=length,
            steps=steps,
            cfg=cfg,
            fps=fps,
            noise_seed=noise_seed
        )

        # 准备工作流
        workflow = prepare_workflow(request)

        # 提交到 ComfyUI
        prompt_id = await submit_workflow(workflow)

        return VideoGenerationResponse(
            prompt_id=prompt_id,
            status="submitted",
            message="Wan2.2 图生视频任务已提交，请使用 prompt_id 查询生成状态"
        )

    except Exception as e:
        logger.error(f"生成视频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate", response_model=VideoGenerationResponse)
async def generate_video_with_filename(request: VideoGenerationRequest):
    """
    使用已存在的图片文件名生成视频

    适用于图片已经在 ComfyUI 服务器上的情况
    """
    try:
        logger.info(f"收到图生视频请求，图片: {request.image_filename}, 提示词: {request.prompt[:50]}...")

        # 准备工作流
        workflow = prepare_workflow(request)

        # 提交到 ComfyUI
        prompt_id = await submit_workflow(workflow)

        return VideoGenerationResponse(
            prompt_id=prompt_id,
            status="submitted",
            message="Wan2.2 图生视频任务已提交，请使用 prompt_id 查询生成状态"
        )

    except Exception as e:
        logger.error(f"生成视频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{prompt_id}")
async def get_task_status(prompt_id: str):
    """
    查询任务状态接口

    根据 prompt_id 查询视频生成任务的状态和结果
    """
    try:
        status_info = await check_workflow_status(prompt_id)

        return {
            "prompt_id": prompt_id,
            "status": status_info.get("status", "unknown"),
            "progress": status_info.get("progress"),
            "videos": status_info.get("videos"),
            "error": status_info.get("error")
        }

    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/enhance_prompt", response_model=PromptEnhanceResponse)
async def enhance_prompt(request: PromptEnhanceRequest):
    """
    提示词优化接口

    使用 DeepSeek AI 将简单的用户提示词扩写为高质量的图生视频提示词。

    该接口会将用户输入的简单描述扩写为包含以下部分的详细提示词：
    - 主体（Subject）：角色/物体外观、服饰道具
    - 场景（Environment）：时间、天气、地点、氛围
    - 运动（Motion）：主体动作、环境交互、镜头运动
    - 美学控制（Aesthetic Controls）：光源、景别、焦段、构图
    - 风格化（Stylization）：流派、材质、色彩策略
    - 反向/禁止项（Negative）：质量控制
    - 参数建议：分辨率、帧率等
    """
    try:
        logger.info(f"收到提示词优化请求，原始提示词: {request.user_prompt[:50]}...")

        # 调用 DeepSeek API 优化提示词
        enhanced_prompt = await enhance_prompt_with_deepseek(
            user_prompt=request.user_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        return PromptEnhanceResponse(
            original_prompt=request.user_prompt,
            enhanced_prompt=enhanced_prompt,
            status="success",
            message="提示词优化成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"优化提示词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload_and_generate_sync")
async def upload_and_generate_video_sync(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    width: int = Form(1280),
    height: int = Form(720),
    length: int = Form(81),
    steps: int = Form(4),
    cfg: float = Form(1.0),
    fps: int = Form(16),
    noise_seed: Optional[int] = Form(None),
    timeout: int = Form(600, description="超时时间（秒）")
):
    """
    同步图生视频（等待完成）

    上传图片后等待视频生成完成，直接返回结果
    """
    try:
        logger.info(f"收到同步图生视频请求，图片: {image.filename}")

        # 读取上传的图片
        image_content = await image.read()

        # 上传图片到 ComfyUI
        uploaded_filename = await upload_image_to_comfyui(image_content, image.filename)

        # 准备请求参数
        request = VideoGenerationRequest(
            image_filename=uploaded_filename,
            prompt=prompt,
            width=width,
            height=height,
            length=length,
            steps=steps,
            cfg=cfg,
            fps=fps,
            noise_seed=noise_seed
        )

        # 准备并提交工作流
        workflow = prepare_workflow(request)
        prompt_id = await submit_workflow(workflow)

        # 轮询等待完成
        start_time = time.time()
        while time.time() - start_time < timeout:
            status_info = await check_workflow_status(prompt_id)
            status = status_info.get("status")

            if status == "completed":
                return {
                    "prompt_id": prompt_id,
                    "status": "completed",
                    "videos": status_info.get("videos", []),
                    "message": "视频生成完成"
                }
            elif status == "failed":
                raise HTTPException(
                    status_code=500,
                    detail=f"视频生成失败: {status_info.get('error', 'Unknown error')}"
                )

            # 等待后继续查询
            await asyncio.sleep(5)

        # 超时
        raise HTTPException(
            status_code=408,
            detail=f"视频生成超时（{timeout}秒），请使用异步接口或增加超时时间"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步生成视频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("ComfyUI Wan2.2 I2V 14B 4-steps API Server")
    print("=" * 60)
    print(f"服务地址: http://0.0.0.0:5014")
    print(f"API 文档: http://0.0.0.0:5014/docs")
    print(f"ComfyUI: {COMFYUI_BASE_URL}")
    print(f"模型: Wan2.2-I2V-A14B-4steps")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5014,
        log_level="info"
    )
