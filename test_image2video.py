"""
ComfyUI Image to Video API 测试脚本
测试图生视频功能
"""

import requests
import time
import json
import os
from pathlib import Path

# 清除代理环境变量
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('all_proxy', None)

# API 配置
API_BASE_URL = "http://localhost:8001"

# 创建禁用代理的 session
session = requests.Session()
session.trust_env = False

# 测试图片路径
TEST_IMAGE_PATH = Path.home() / "Pictures" / "train-suiji" / "8ly7og0x.jpeg"

# 测试提示词
TEST_PROMPT = """A young woman in traditional Chinese-style clothing stands in profile, not looking at the camera. She shyly turns her head toward the camera, her lips curling into a gentle, sweet smile. With a graceful motion, she begins to perform a short traditional dance — her sleeves flow lightly as she moves, exuding elegance and charm. Her expressions are soft, shy, and emotionally rich. The lighting is soft and cinematic, the atmosphere calm and romantic, with a warm, dreamy tone."""


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def test_health_check():
    """测试健康检查"""
    print_section("测试 1: 健康检查")

    try:
        response = session.get(f"{API_BASE_URL}/health", timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False


def test_upload_and_generate():
    """测试上传图片并生成视频"""
    print_section("测试 2: 上传图片并生成视频")

    # 检查测试图片是否存在
    if not TEST_IMAGE_PATH.exists():
        print(f"❌ 测试图片不存在: {TEST_IMAGE_PATH}")
        print(f"请确认图片路径是否正确")
        return None

    print(f"测试图片: {TEST_IMAGE_PATH}")
    print(f"图片大小: {TEST_IMAGE_PATH.stat().st_size / 1024:.2f} KB")
    print(f"\n提示词:")
    print(TEST_PROMPT[:100] + "...")

    try:
        # 准备请求数据
        files = {
            'image': (TEST_IMAGE_PATH.name, open(TEST_IMAGE_PATH, 'rb'), 'image/jpeg')
        }

        data = {
            'prompt': TEST_PROMPT,
            'width': 768,
            'height': 768,
            'length': 81,  # 81帧，约5秒视频
            'steps': 20,
            'cfg': 3.5,
            'fps': 16
        }

        print(f"\n请求参数:")
        print(json.dumps({k: v for k, v in data.items() if k != 'prompt'}, indent=2))
        print(f"prompt: {data['prompt'][:50]}...")

        # 提交生成任务
        print("\n📤 上传图片并提交生成任务...")
        response = session.post(
            f"{API_BASE_URL}/api/upload_and_generate",
            files=files,
            data=data,
            timeout=60
        )

        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if response.status_code != 200:
            print("❌ 任务提交失败")
            return None

        prompt_id = result.get("prompt_id")
        print(f"\n✅ 任务已提交，prompt_id: {prompt_id}")

        # 轮询查询状态
        print("\n⏳ 等待视频生成完成...")
        print("⚠️  注意: 视频生成可能需要较长时间（5-15分钟），请耐心等待...")
        max_attempts = 300  # 最多等待 25 分钟（每5秒查询一次）
        attempt = 0

        while attempt < max_attempts:
            time.sleep(5)  # 视频生成时间较长，5秒查询一次
            attempt += 1

            status_response = session.get(
                f"{API_BASE_URL}/api/status/{prompt_id}",
                timeout=10
            )

            status_data = status_response.json()
            status = status_data.get("status")

            # 显示进度
            elapsed_time = attempt * 5
            print(f"[{elapsed_time}s] 状态: {status}", end="")

            if status_data.get("progress") is not None:
                print(f" - 进度: {status_data.get('progress')}%")
            else:
                print()

            if status == "completed":
                print("\n✅ 视频生成完成！")
                print(f"\n生成结果:")
                print(json.dumps(status_data, indent=2, ensure_ascii=False))

                videos = status_data.get("videos", [])
                if videos:
                    print(f"\n生成了 {len(videos)} 个视频:")
                    for i, video in enumerate(videos, 1):
                        print(f"\n  视频 {i}:")
                        print(f"    格式: {video.get('format')}")
                        print(f"    文件名: {video.get('filename')}")
                        print(f"    URL: {video.get('url')}")
                        print(f"\n    在浏览器中打开查看:")
                        print(f"    {video.get('url')}")

                return status_data

            elif status == "failed":
                print(f"\n❌ 视频生成失败: {status_data.get('error')}")
                return None

        print("\n⏰ 超时：视频生成时间过长")
        print(f"任务可能仍在处理中，可以继续手动查询: {API_BASE_URL}/api/status/{prompt_id}")
        return None

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # 确保文件关闭
        if 'files' in locals() and files.get('image'):
            files['image'][1].close()


def test_with_curl():
    """生成 curl 测试命令"""
    print_section("使用 curl 测试")

    print("\n1️⃣  上传图片并生成视频（异步）:")
    curl_upload = f"""curl -X POST "{API_BASE_URL}/api/upload_and_generate" \\
  -F "image=@{TEST_IMAGE_PATH}" \\
  -F "prompt={TEST_PROMPT[:50]}..." \\
  -F "width=768" \\
  -F "height=768" \\
  -F "length=81" \\
  -F "steps=20" \\
  -F "cfg=3.5" \\
  -F "fps=16" """
    print(curl_upload)

    print("\n\n2️⃣  查询状态:")
    curl_status = """curl -X GET "http://localhost:8001/api/status/PROMPT_ID" """
    print(curl_status)

    print("\n\n3️⃣  如果图片已在服务器上，使用文件名生成:")
    curl_generate = """curl -X POST "http://localhost:8001/api/generate" \\
  -H "Content-Type: application/json" \\
  -d '{
    "image_filename": "bf635fbb-a7a7-482b-b946-d3d15fb2b82b.jpeg",
    "prompt": "A young woman looks...",
    "width": 768,
    "height": 768,
    "length": 81,
    "steps": 20,
    "cfg": 3.5,
    "fps": 16
  }'"""
    print(curl_generate)


def main():
    """主测试流程"""
    print("\n" + "🎬" * 30)
    print("ComfyUI Image to Video API 测试套件")
    print("🎬" * 30)

    # 1. 健康检查
    if not test_health_check():
        print("\n⚠️  警告: 服务健康检查失败，但继续测试...")

    # 等待一下
    time.sleep(1)

    # 2. 测试上传并生成视频
    result = test_upload_and_generate()

    if result:
        print("\n" + "✅" * 30)
        print("测试通过！视频生成成功")
        print("✅" * 30)
    else:
        print("\n" + "❌" * 30)
        print("测试失败！")
        print("❌" * 30)

    # 3. 显示 curl 命令
    test_with_curl()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n💡 提示:")
    print("  - 查看 API 文档: http://localhost:8001/docs")
    print("  - 查看根路径: http://localhost:8001/")
    print("  - 健康检查: http://localhost:8001/health")
    print("\n⚠️  注意:")
    print("  - 视频生成需要较长时间（5-15分钟），请耐心等待")
    print("  - 生成时间取决于视频长度和服务器性能")
    print("  - 可以在浏览器中打开生成的视频 URL 查看结果")


if __name__ == "__main__":
    main()
