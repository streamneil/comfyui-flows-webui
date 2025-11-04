"""
ComfyUI Qwen Image Generation API Server
基于 FastAPI 的 ComfyUI 工作流调用服务
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import httpx
import json
import uuid
import asyncio
import time
from typing import Optional, Dict, Any
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ComfyUI Qwen Image API",
    description="基于 ComfyUI Qwen Image 工作流的图片生成服务",
    version="1.0.0"
)

# ComfyUI 服务配置
COMFYUI_BASE_URL = "http://60.169.65.100:5000"
COMFYUI_API_URL = f"{COMFYUI_BASE_URL}/cfui/api"
COMFYUI_WS_URL = f"ws://60.169.65.100:5000/ws"

# 加载工作流模板
WORKFLOW_TEMPLATE_PATH = Path(__file__).parent / "L3_Qwen_Image.json"


class ImageGenerationRequest(BaseModel):
    """图片生成请求模型"""
    prompt: str = Field(..., description="生成图片的提示词", min_length=1)
    seed: Optional[int] = Field(None, description="随机种子，不指定则随机生成")
    steps: int = Field(20, description="采样步数", ge=1, le=150)
    cfg: float = Field(2.5, description="CFG 系数", ge=0.0, le=30.0)
    width: int = Field(1328, description="图片宽度", ge=512, le=2048)
    height: int = Field(1328, description="图片高度", ge=512, le=2048)
    sampler_name: str = Field("euler", description="采样器名称")
    scheduler: str = Field("simple", description="调度器")


class ImageGenerationResponse(BaseModel):
    """图片生成响应模型"""
    prompt_id: str = Field(..., description="任务提示ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="响应消息")


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    prompt_id: str
    status: str
    progress: Optional[float] = None
    images: Optional[list] = None
    error: Optional[str] = None


def load_workflow_template() -> Dict[str, Any]:
    """加载工作流模板"""
    try:
        with open(WORKFLOW_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载工作流模板失败: {e}")
        raise RuntimeError(f"无法加载工作流模板: {e}")


def prepare_workflow(request: ImageGenerationRequest) -> Dict[str, Any]:
    """根据请求参数准备工作流"""
    workflow =  load_workflow_template()

    # 更新提示词（节点 6）
    if "6" in workflow:
        workflow["6"]["inputs"]["text"] = request.prompt

    # 更新采样参数（节点 3）
    if "3" in workflow:
        workflow["3"]["inputs"]["seed"] = request.seed if request.seed else int(time.time() * 1000000) % (2**32)
        workflow["3"]["inputs"]["steps"] = request.steps
        workflow["3"]["inputs"]["cfg"] = request.cfg
        workflow["3"]["inputs"]["sampler_name"] = request.sampler_name
        workflow["3"]["inputs"]["scheduler"] = request.scheduler

    # 更新图片尺寸（节点 58）
    if "58" in workflow:
        workflow["58"]["inputs"]["width"] = request.width
        workflow["58"]["inputs"]["height"] = request.height

    return workflow


async def submit_workflow(workflow: Dict[str, Any]) -> str:
    """提交工作流到 ComfyUI"""
    prompt_id = str(uuid.uuid4())

    payload = {
        "prompt": workflow,
        "client_id": prompt_id
    }

    # 禁用代理，直接连接（适用于本地服务）
    async with httpx.AsyncClient(timeout=30.0, proxies={}) as client:
        try:
            response = await client.post(
                f"{COMFYUI_API_URL}/prompt",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            # ComfyUI 返回的 prompt_id
            actual_prompt_id = result.get("prompt_id", prompt_id)
            logger.info(f"工作流提交成功，prompt_id: {actual_prompt_id}")
            return actual_prompt_id

        except httpx.HTTPError as e:
            logger.error(f"提交工作流失败: {e}")
            raise HTTPException(status_code=500, detail=f"提交工作流失败: {str(e)}")


async def check_workflow_status(prompt_id: str) -> Dict[str, Any]:
    """检查工作流执行状态"""
    # 禁用代理，直接连接（适用于本地服务）
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
                    images = []

                    # 提取生成的图片信息
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for img in node_output["images"]:
                                images.append({
                                    "filename": img.get("filename"),
                                    "subfolder": img.get("subfolder", ""),
                                    "type": img.get("type", "output"),
                                    "url": f"{COMFYUI_BASE_URL}/cfui/view?filename={img.get('filename')}&subfolder={img.get('subfolder', '')}&type={img.get('type', 'output')}"
                                })

                    return {
                        "status": "completed",
                        "images": images
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
        "service": "ComfyUI Qwen Image API",
        "version": "1.0.0",
        "endpoints": {
            "generate": "/api/generate",
            "status": "/api/status/{prompt_id}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 禁用代理，直接连接（适用于本地服务）
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


@app.post("/api/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    生成图片接口

    接收提示词和生成参数，调用 ComfyUI 工作流生成图片
    """
    try:
        logger.info(f"收到图片生成请求，提示词: {request.prompt[:50]}...")

        # 准备工作流
        workflow = prepare_workflow(request)

        # 提交到 ComfyUI
        prompt_id = await submit_workflow(workflow)

        return ImageGenerationResponse(
            prompt_id=prompt_id,
            status="submitted",
            message="图片生成任务已提交，请使用 prompt_id 查询生成状态"
        )

    except Exception as e:
        logger.error(f"生成图片失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{prompt_id}", response_model=TaskStatusResponse)
async def get_task_status(prompt_id: str):
    """
    查询任务状态接口

    根据 prompt_id 查询图片生成任务的状态和结果
    """
    try:
        status_info = await check_workflow_status(prompt_id)

        return TaskStatusResponse(
            prompt_id=prompt_id,
            status=status_info.get("status", "unknown"),
            progress=status_info.get("progress"),
            images=status_info.get("images"),
            error=status_info.get("error")
        )

    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate_sync")
async def generate_image_sync(request: ImageGenerationRequest, timeout: int = 300):
    """
    同步生成图片接口（等待完成）

    提交任务后等待生成完成，直接返回结果
    """
    try:
        logger.info(f"收到同步图片生成请求，提示词: {request.prompt[:50]}...")

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
                    "images": status_info.get("images", []),
                    "message": "图片生成完成"
                }
            elif status == "failed":
                raise HTTPException(
                    status_code=500,
                    detail=f"图片生成失败: {status_info.get('error', 'Unknown error')}"
                )

            # 等待后继续查询
            await asyncio.sleep(2)

        # 超时
        raise HTTPException(
            status_code=408,
            detail=f"图片生成超时（{timeout}秒），请使用异步接口或增加超时时间"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步生成图片失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("ComfyUI Qwen Image API Server")
    print("=" * 60)
    print(f"服务地址: http://0.0.0.0:8000")
    print(f"API 文档: http://0.0.0.0:8000/docs")
    print(f"ComfyUI: {COMFYUI_BASE_URL}")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
