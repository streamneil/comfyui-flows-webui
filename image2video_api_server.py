"""
ComfyUI Image to Video API Server
基于 FastAPI 的图生视频工作流调用服务
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

from fastapi.middleware.cors import CORSMiddleware

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ComfyUI Image to Video API",
    description="基于 ComfyUI 的图生视频服务",
    version="1.0.0"
)
# 在创建 app 之后立即添加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ComfyUI 服务配置
COMFYUI_BASE_URL = "http://60.169.65.100:5000"
COMFYUI_API_URL = f"{COMFYUI_BASE_URL}/cfui/api"

# 加载工作流模板
WORKFLOW_TEMPLATE_PATH = Path(__file__).parent / "Image_2_Video_KSampler_Advanced.json"


class VideoGenerationRequest(BaseModel):
    """视频生成请求模型"""
    image_filename: str = Field(..., description="上传到 ComfyUI 的图片文件名")
    prompt: str = Field(..., description="正向提示词", min_length=1)
    width: int = Field(768, description="视频宽度", ge=512, le=1920)
    height: int = Field(768, description="视频高度", ge=512, le=1920)
    length: int = Field(81, description="视频帧数", ge=16, le=240)
    steps: int = Field(15, description="采样步数", ge=10, le=50)
    cfg: float = Field(3.5, description="CFG 系数", ge=1.0, le=20.0)
    noise_seed: Optional[int] = Field(None, description="随机种子")
    fps: int = Field(16, description="帧率", ge=8, le=60)


class VideoGenerationResponse(BaseModel):
    """视频生成响应模型"""
    prompt_id: str = Field(..., description="任务提示ID")
    status: str = Field(..., description="任务状态")
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

    # 更新图片文件名（节点 52）
    if "52" in workflow:
        workflow["52"]["inputs"]["image"] = request.image_filename

    # 更新视频参数（节点 50 - WanImageToVideo）
    if "50" in workflow:
        workflow["50"]["inputs"]["width"] = request.width
        workflow["50"]["inputs"]["height"] = request.height
        workflow["50"]["inputs"]["length"] = request.length

    # 更新第一阶段采样器参数（节点 57 - KSamplerAdvanced）
    if "57" in workflow:
        workflow["57"]["inputs"]["steps"] = request.steps
        workflow["57"]["inputs"]["cfg"] = request.cfg
        if request.noise_seed:
            workflow["57"]["inputs"]["noise_seed"] = request.noise_seed
        else:
            workflow["57"]["inputs"]["noise_seed"] = int(time.time() * 1000000) % (2**32)

    # 更新第二阶段采样器参数（节点 58）
    if "58" in workflow:
        workflow["58"]["inputs"]["steps"] = request.steps
        workflow["58"]["inputs"]["cfg"] = request.cfg

    # 更新输出视频帧率（节点 28 和 47）
    if "28" in workflow:
        workflow["28"]["inputs"]["fps"] = request.fps
    if "47" in workflow:
        workflow["47"]["inputs"]["fps"] = float(request.fps)

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

                    # 提取生成的视频信息
                    for node_id, node_output in outputs.items():
                        # 检查 WEBP 输出（节点 28）
                        if "images" in node_output:
                            for item in node_output["images"]:
                                videos.append({
                                    "filename": item.get("filename"),
                                    "subfolder": item.get("subfolder", ""),
                                    "type": item.get("type", "output"),
                                    "format": "webp",
                                    "url": f"{COMFYUI_BASE_URL}/cfui/view?filename={item.get('filename')}&subfolder={item.get('subfolder', '')}&type={item.get('type', 'output')}"
                                })
                        # 检查 WEBM 输出（节点 47）
                        if "gifs" in node_output:
                            for item in node_output["gifs"]:
                                videos.append({
                                    "filename": item.get("filename"),
                                    "subfolder": item.get("subfolder", ""),
                                    "type": item.get("type", "output"),
                                    "format": "webm",
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
        "service": "ComfyUI Image to Video API",
        "version": "1.0.0",
        "endpoints": {
            "upload_and_generate": "/api/upload_and_generate",
            "generate_with_filename": "/api/generate",
            "status": "/api/status/{prompt_id}",
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
    width: int = Form(768, description="视频宽度"),
    height: int = Form(768, description="视频高度"),
    length: int = Form(81, description="视频帧数"),
    steps: int = Form(20, description="采样步数"),
    cfg: float = Form(3.5, description="CFG系数"),
    fps: int = Form(16, description="帧率"),
    noise_seed: Optional[int] = Form(None, description="随机种子")
):
    """
    上传图片并生成视频（一步到位）

    上传图片文件，设置参数，直接生成视频
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
            message="图生视频任务已提交，请使用 prompt_id 查询生成状态"
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
            message="图生视频任务已提交，请使用 prompt_id 查询生成状态"
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


@app.post("/api/upload_and_generate_sync")
async def upload_and_generate_video_sync(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    width: int = Form(768),
    height: int = Form(768),
    length: int = Form(81),
    steps: int = Form(20),
    cfg: float = Form(3.5),
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
    print("ComfyUI Image to Video API Server")
    print("=" * 60)
    print(f"服务地址: http://0.0.0.0:8001")
    print(f"API 文档: http://0.0.0.0:8001/docs")
    print(f"ComfyUI: {COMFYUI_BASE_URL}")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # 使用不同的端口避免冲突
        log_level="info"
    )
