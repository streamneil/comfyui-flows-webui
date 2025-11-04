#!/usr/bin/env python3
"""
Wan2.2 I2V 14B 4-steps Service 测试脚本
测试所有 API 端点的功能
"""

import requests
import time
import os
import sys
from pathlib import Path
import json

# 配置
API_BASE_URL = "http://localhost:5014"
TEST_IMAGE_PATH = os.path.expanduser("/Users/neil/Downloads/t-w22i2v14b4.jpeg")

# 测试参数
TEST_PARAMS = {
    "prompt": "开心的女孩微笑着，自然的光线，温馨的氛围，高质量",
    "width": 1280,
    "height": 720,
    "length": 81,
    "steps": 4,
    "cfg": 1.0,
    "fps": 16
}

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """打印标题"""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text):
    """打印信息"""
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")


def check_image_exists():
    """检查测试图片是否存在"""
    print_header("检查测试图片")

    if not os.path.exists(TEST_IMAGE_PATH):
        print_error(f"测试图片不存在: {TEST_IMAGE_PATH}")
        print_info("请确保图片路径正确")
        return False

    file_size = os.path.getsize(TEST_IMAGE_PATH) / 1024  # KB
    print_success(f"找到测试图片: {TEST_IMAGE_PATH}")
    print_info(f"图片大小: {file_size:.2f} KB")
    return True


def test_health_check():
    """测试健康检查接口"""
    print_header("测试 1: 健康检查")

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        response.raise_for_status()

        data = response.json()
        print_success("健康检查通过")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        return data.get("status") == "healthy"

    except requests.exceptions.ConnectionError:
        print_error("无法连接到服务，请确保服务已启动")
        print_info(f"服务地址: {API_BASE_URL}")
        return False
    except Exception as e:
        print_error(f"健康检查失败: {str(e)}")
        return False


def test_root_endpoint():
    """测试根路径"""
    print_header("测试 2: 根路径信息")

    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        response.raise_for_status()

        data = response.json()
        print_success("获取服务信息成功")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return True

    except Exception as e:
        print_error(f"获取服务信息失败: {str(e)}")
        return False


def test_upload_and_generate_async():
    """测试异步上传并生成视频"""
    print_header("测试 3: 异步上传并生成视频")

    try:
        # 准备文件和参数
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': (os.path.basename(TEST_IMAGE_PATH), f, 'image/jpeg')}

            data = {
                'prompt': TEST_PARAMS['prompt'],
                'width': TEST_PARAMS['width'],
                'height': TEST_PARAMS['height'],
                'length': TEST_PARAMS['length'],
                'steps': TEST_PARAMS['steps'],
                'cfg': TEST_PARAMS['cfg'],
                'fps': TEST_PARAMS['fps']
            }

            print_info("正在上传图片并提交任务...")
            response = requests.post(
                f"{API_BASE_URL}/api/upload_and_generate",
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()

        result = response.json()
        print_success("任务提交成功")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        prompt_id = result.get('prompt_id')
        if prompt_id:
            print_info(f"获得 prompt_id: {prompt_id}")
            return prompt_id
        else:
            print_error("未获得 prompt_id")
            return None

    except Exception as e:
        print_error(f"上传并生成失败: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print_error(f"响应内容: {e.response.text}")
        return None


def test_check_status(prompt_id, max_attempts=120, interval=5):
    """测试查询任务状态"""
    print_header("测试 4: 查询任务状态")

    if not prompt_id:
        print_error("没有有效的 prompt_id，跳过状态查询")
        return None

    print_info(f"开始轮询任务状态 (最多 {max_attempts * interval} 秒)")

    for attempt in range(max_attempts):
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/status/{prompt_id}",
                timeout=10
            )
            response.raise_for_status()

            status_info = response.json()
            status = status_info.get('status', 'unknown')

            print(f"\r第 {attempt + 1} 次查询 - 状态: {status}", end='', flush=True)

            if status == 'completed':
                print()  # 换行
                print_success("任务完成！")
                print(json.dumps(status_info, indent=2, ensure_ascii=False))
                return status_info

            elif status == 'failed':
                print()  # 换行
                print_error(f"任务失败: {status_info.get('error', 'Unknown error')}")
                return status_info

            elif status in ['pending', 'running']:
                time.sleep(interval)

            else:
                print()  # 换行
                print_error(f"未知状态: {status}")
                return status_info

        except Exception as e:
            print()  # 换行
            print_error(f"查询状态失败: {str(e)}")
            return None

    print()  # 换行
    print_error(f"任务超时（{max_attempts * interval} 秒）")
    return None


def test_sync_generation():
    """测试同步生成（可选，耗时较长）"""
    print_header("测试 5: 同步生成视频（可选）")

    print_info("同步生成会等待任务完成，可能需要 10 分钟左右")
    print_info("按 Enter 继续测试，或输入 'skip' 跳过")

    user_input = input().strip().lower()
    if user_input == 'skip':
        print_info("跳过同步生成测试")
        return None

    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': (os.path.basename(TEST_IMAGE_PATH), f, 'image/jpeg')}

            data = {
                'prompt': TEST_PARAMS['prompt'],
                'width': TEST_PARAMS['width'],
                'height': TEST_PARAMS['height'],
                'length': TEST_PARAMS['length'],
                'steps': TEST_PARAMS['steps'],
                'cfg': TEST_PARAMS['cfg'],
                'fps': TEST_PARAMS['fps'],
                'timeout': 600  # 10 分钟超时
            }

            print_info("正在同步生成视频，请等待...")
            response = requests.post(
                f"{API_BASE_URL}/api/upload_and_generate_sync",
                files=files,
                data=data,
                timeout=610  # 略大于服务端超时
            )
            response.raise_for_status()

        result = response.json()
        print_success("同步生成完成")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    except requests.exceptions.Timeout:
        print_error("请求超时")
        return None
    except Exception as e:
        print_error(f"同步生成失败: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print_error(f"响应内容: {e.response.text}")
        return None


def display_results(status_info):
    """显示最终结果"""
    print_header("测试结果摘要")

    if not status_info:
        print_error("未能获取任务结果")
        return

    status = status_info.get('status')

    if status == 'completed':
        videos = status_info.get('videos', [])

        if videos:
            print_success(f"成功生成 {len(videos)} 个视频")
            print()

            for i, video in enumerate(videos, 1):
                print(f"{Colors.BOLD}视频 {i}:{Colors.END}")
                print(f"  文件名: {video.get('filename')}")
                print(f"  格式: {video.get('format')}")
                print(f"  URL: {video.get('url')}")
                print()

            print_info("你可以通过上面的 URL 下载或预览视频")
        else:
            print_error("任务完成但没有生成视频")

    elif status == 'failed':
        print_error(f"任务失败: {status_info.get('error', 'Unknown error')}")

    else:
        print_error(f"任务状态: {status}")


def main():
    """主测试流程"""
    print_header("Wan2.2 I2V 14B 4-steps 服务测试")

    print(f"服务地址: {API_BASE_URL}")
    print(f"测试图片: {TEST_IMAGE_PATH}")
    print(f"提示词: {TEST_PARAMS['prompt']}")
    print(f"参数: {TEST_PARAMS['width']}x{TEST_PARAMS['height']}, "
          f"{TEST_PARAMS['length']}帧, {TEST_PARAMS['steps']}步, "
          f"CFG={TEST_PARAMS['cfg']}, {TEST_PARAMS['fps']}fps")

    # 1. 检查图片
    if not check_image_exists():
        sys.exit(1)

    # 2. 健康检查
    if not test_health_check():
        print_error("服务未就绪，请先启动服务")
        print_info("运行: ./start_wan22_service.sh")
        sys.exit(1)

    # 3. 测试根路径
    test_root_endpoint()

    # 4. 异步上传并生成
    prompt_id = test_upload_and_generate_async()

    if not prompt_id:
        print_error("无法继续测试，因为任务提交失败")
        sys.exit(1)

    # 5. 查询状态直到完成
    status_info = test_check_status(prompt_id)

    # 6. 显示结果
    display_results(status_info)

    # 7. 可选：测试同步生成
    # test_sync_generation()

    print_header("测试完成")

    if status_info and status_info.get('status') == 'completed':
        print_success("所有测试通过！")
        sys.exit(0)
    else:
        print_error("部分测试未通过")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n")
        print_info("测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print("\n\n")
        print_error(f"测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
