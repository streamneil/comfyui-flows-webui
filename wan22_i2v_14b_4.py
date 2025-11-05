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
import base64

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
            "然后编辑 config.ini 填入 Moonshot API Key"
        )

    config.read(config_path, encoding='utf-8')
    return config


# 加载配置
try:
    config = load_config()

    # ComfyUI 服务配置
    COMFYUI_BASE_URL = config.get('comfyui', 'base_url', fallback='http://60.169.65.100:5000')
    COMFYUI_API_URL = f"{COMFYUI_BASE_URL}/cfui/api"

    # Moonshot AI API 配置
    MOONSHOT_API_KEY = config.get('moonshot', 'api_key', fallback='')
    MOONSHOT_API_URL = config.get('moonshot', 'api_url', fallback='https://api.moonshot.cn/v1/chat/completions')
    MOONSHOT_MODEL = config.get('moonshot', 'model', fallback='moonshot-v1-8k')

    if not MOONSHOT_API_KEY:
        logger.warning("Moonshot API Key 未配置，提示词优化功能将不可用")
    else:
        logger.info("Moonshot API Key 已加载")

except Exception as e:
    logger.error(f"加载配置文件失败: {e}")
    # 使用默认配置
    COMFYUI_BASE_URL = "http://60.169.65.100:5000"
    COMFYUI_API_URL = f"{COMFYUI_BASE_URL}/cfui/api"
    MOONSHOT_API_KEY = ""
    MOONSHOT_API_URL = "https://api.moonshot.cn/v1/chat/completions"
    MOONSHOT_MODEL = "moonshot-v1-8k"


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
PROMPT_ENHANCE_SYSTEM_MESSAGE = """
你是一个专业的视频创作助手，请根据用户输入的提示词，扩展出更高质量的视频提示词，确保适合生成一个5秒的图生视频：

要求：
1. 输出结果必须是完整的一段话，控制在500字以内，语言精炼，表达准确，避免冗余。尽量使用简单的词语和句子结构。
2. 这段话应包含：主体描述、背景描述、运动描述、光线氛围等元素。
3. 运动描述要符合物理规律，避免非常复杂的物理动作（如球类的弹跳、高空抛物等）。
4. 运动变化幅度不能过大，要适合5秒短视频。
5. 基于用户的简单提示词，合理推断和补充细节，使描述更加生动具体。

请直接输出优化后的提示词，不要有其他说明文字。
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


async def enhance_prompt_with_moonshot(
    user_prompt: str,
    image_data: Optional[bytes] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> str:
    """
    使用 Moonshot AI API 优化提示词（支持视觉输入）

    Args:
        user_prompt: 用户输入的提示词
        image_data: 图片二进制数据（可选，支持视觉分析）
        temperature: 生成温度
        max_tokens: 最大token数

    Returns:
        优化后的提示词
    """
    if not MOONSHOT_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Moonshot API Key 未配置，请在 config.ini 文件中配置 [moonshot] api_key"
        )

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MOONSHOT_API_KEY}"
        }

        # 构建用户消息内容
        user_content = []

        # 如果有图片，先添加图片
        if image_data:
            # 将图片转换为 base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            logger.info(f"已接收图片数据（{len(image_data)} bytes），正在使用视觉模型分析")

            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}"
                }
            })

        # 添加文本提示词
        user_content.append({
            "type": "text",
            "text": user_prompt
        })

        # 构建消息
        payload = {
            "model": MOONSHOT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": PROMPT_ENHANCE_SYSTEM_MESSAGE
                },
                {
                    "role": "user",
                    "content": user_content if image_data else user_prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=120.0, proxies={}) as client:
            response = await client.post(
                MOONSHOT_API_URL,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()

            # 提取生成的内容
            enhanced_prompt = result["choices"][0]["message"]["content"]
            logger.info(f"提示词优化成功，原始长度: {len(user_prompt)}, 优化后长度: {len(enhanced_prompt)}")
            if image_data:
                logger.info("已使用视觉模型分析图片内容")
            return enhanced_prompt

    except httpx.HTTPError as e:
        logger.error(f"调用 Moonshot API 失败: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"响应内容: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"调用 Moonshot API 失败: {str(e)}")
    except KeyError as e:
        logger.error(f"解析 Moonshot API 响应失败: {e}")
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
async def enhance_prompt(
    user_prompt: str = Form(..., description="用户输入的简单提示词"),
    image: Optional[UploadFile] = File(None, description="要转换为视频的图片（支持视觉分析）"),
    temperature: float = Form(0.7, description="生成温度"),
    max_tokens: int = Form(2000, description="最大生成token数")
):
    """
    提示词优化接口

    使用 Moonshot AI 视觉模型根据用户提示词和图片，生成高质量的图生视频提示词。

    **支持视觉输入**：Moonshot AI 支持图片分析，可以结合图片内容生成更准确的提示词。

    该接口会根据用户描述和图片内容，生成包含以下部分的详细提示词：
    - 主体描述：详细的主体特征
    - 背景描述：场景和环境细节
    - 运动描述：合理的动作和变化
    - 其他细节：光线、氛围等

    参数：
    - user_prompt: 用户的简单提示词（必填）
    - image: 图片文件（可选，支持视觉分析）
    - temperature: 生成温度，默认 0.7
    - max_tokens: 最大生成 token 数，默认 2000
    """
    try:
        logger.info(f"收到提示词优化请求，原始提示词: {user_prompt[:50]}...")

        # 读取图片数据（如果有）
        image_data = None
        if image:
            image_data = await image.read()
            logger.info(f"已接收图片: {image.filename}, 大小: {len(image_data)} bytes")
        else:
            logger.info("未上传图片，仅使用文本提示词")

        # 调用 Moonshot API 优化提示词
        enhanced_prompt = await enhance_prompt_with_moonshot(
            user_prompt=user_prompt,
            image_data=image_data,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return PromptEnhanceResponse(
            original_prompt=user_prompt,
            enhanced_prompt=enhanced_prompt,
            status="success",
            message="提示词优化成功" + ("（已使用视觉模型分析图片内容）" if image_data else "")
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
