"""
ComfyUI API 测试脚本
测试图片生成功能
"""

import requests
import time
import json
import os
from typing import Dict, Any

# 清除代理环境变量，避免 SOCKS 代理问题
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('all_proxy', None)

# API 配置
API_BASE_URL = "http://localhost:8000"

# 创建禁用代理的 session
session = requests.Session()
session.trust_env = False  # 禁用环境变量代理


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


def test_async_generation():
    """测试异步图片生成"""
    print_section("测试 2: 异步图片生成")

    # 请求参数
    request_data = {
        "prompt": "一只小猫在喝咖啡",
        "steps": 20,
        "cfg": 2.5,
        "width": 1328,
        "height": 1328,
        "sampler_name": "euler",
        "scheduler": "simple"
    }

    print(f"请求参数:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))

    try:
        # 提交生成任务
        print("\n📤 提交生成任务...")
        response = session.post(
            f"{API_BASE_URL}/api/generate",
            json=request_data,
            timeout=30
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
        print("\n⏳ 等待生成完成...")
        max_attempts = 150  # 最多等待 5 分钟
        attempt = 0

        while attempt < max_attempts:
            time.sleep(2)
            attempt += 1

            status_response = session.get(
                f"{API_BASE_URL}/api/status/{prompt_id}",
                timeout=10
            )

            status_data = status_response.json()
            status = status_data.get("status")

            print(f"[{attempt}] 状态: {status}", end="")

            if status_data.get("progress") is not None:
                print(f" - 进度: {status_data.get('progress')}%")
            else:
                print()

            if status == "completed":
                print("\n✅ 生成完成！")
                print(f"\n生成结果:")
                print(json.dumps(status_data, indent=2, ensure_ascii=False))

                images = status_data.get("images", [])
                if images:
                    print(f"\n生成了 {len(images)} 张图片:")
                    for i, img in enumerate(images, 1):
                        print(f"  {i}. {img.get('url')}")

                return status_data

            elif status == "failed":
                print(f"\n❌ 生成失败: {status_data.get('error')}")
                return None

        print("\n⏰ 超时：生成时间过长")
        return None

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return None


def test_sync_generation():
    """测试同步图片生成"""
    print_section("测试 3: 同步图片生成（直接等待结果）")

    request_data = {
        "prompt": "一只小猫在喝咖啡",
        "steps": 20,
        "cfg": 2.5,
        "width": 1328,
        "height": 1328
    }

    print(f"请求参数:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))

    try:
        print("\n📤 提交同步生成任务（等待完成）...")
        response = session.post(
            f"{API_BASE_URL}/api/generate_sync",
            json=request_data,
            params={"timeout": 300},  # 5分钟超时
            timeout=310  # 客户端超时稍长
        )

        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"\n生成结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if response.status_code == 200:
            images = result.get("images", [])
            if images:
                print(f"\n✅ 生成成功！共 {len(images)} 张图片:")
                for i, img in enumerate(images, 1):
                    print(f"  {i}. {img.get('url')}")
            return result
        else:
            print("❌ 同步生成失败")
            return None

    except requests.Timeout:
        print("\n⏰ 请求超时")
        return None
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return None


def test_with_curl():
    """生成 curl 测试命令"""
    print_section("使用 curl 测试")

    print("\n1️⃣  异步生成（推荐）:")
    print("\n# 提交任务")
    curl_generate = """curl -X POST "http://localhost:8000/api/generate" \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "一只小猫在喝咖啡",
    "steps": 20,
    "cfg": 2.5,
    "width": 1328,
    "height": 1328
  }'"""
    print(curl_generate)

    print("\n# 查询状态（将 PROMPT_ID 替换为上面返回的 prompt_id）")
    curl_status = """curl -X GET "http://localhost:8000/api/status/PROMPT_ID" """
    print(curl_status)

    print("\n\n2️⃣  同步生成:")
    curl_sync = """curl -X POST "http://localhost:8000/api/generate_sync" \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "一只小猫在喝咖啡",
    "steps": 20,
    "cfg": 2.5,
    "width": 1328,
    "height": 1328
  }'"""
    print(curl_sync)


def main():
    """主测试流程"""
    print("\n" + "🚀" * 30)
    print("ComfyUI Qwen Image API 测试套件")
    print("🚀" * 30)

    # 1. 健康检查
    if not test_health_check():
        print("\n⚠️  警告: 服务健康检查失败，但继续测试...")

    # 等待一下
    time.sleep(1)

    # 2. 测试异步生成
    result = test_async_generation()

    if result:
        print("\n" + "✅" * 30)
        print("异步测试通过！")
        print("✅" * 30)
    else:
        print("\n" + "❌" * 30)
        print("异步测试失败！")
        print("❌" * 30)

    # 3. 显示 curl 命令
    test_with_curl()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n💡 提示:")
    print("  - 查看 API 文档: http://localhost:8000/docs")
    print("  - 查看根路径: http://localhost:8000/")
    print("  - 健康检查: http://localhost:8000/health")


if __name__ == "__main__":
    main()
