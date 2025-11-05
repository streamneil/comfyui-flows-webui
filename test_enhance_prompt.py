"""
测试 enhance_prompt 接口是否能识别图片内容

此脚本用于验证 /api/enhance_prompt 接口在上传图片时的行为
"""

import requests
import json
from pathlib import Path
import argparse
from PIL import Image
import io


# API 配置
API_BASE_URL = "http://localhost:5014"
ENHANCE_PROMPT_URL = f"{API_BASE_URL}/api/enhance_prompt"


def create_test_image(text: str, color: tuple = (255, 0, 0)) -> bytes:
    """
    创建一个带有文字的测试图片

    Args:
        text: 要在图片上显示的文字
        color: 背景颜色 RGB

    Returns:
        图片的字节数据
    """
    from PIL import ImageDraw, ImageFont

    # 创建一个简单的图片
    img = Image.new('RGB', (800, 600), color=color)
    draw = ImageDraw.Draw(img)

    # 添加文字
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except:
        # 如果没有找到字体，使用默认字体
        font = ImageFont.load_default()

    # 在图片中心绘制文字
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (800 - text_width) // 2
    y = (600 - text_height) // 2
    draw.text((x, y), text, fill=(255, 255, 255), font=font)

    # 保存到字节流
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)

    return img_bytes.getvalue()


def test_enhance_prompt_with_image(
    user_prompt: str,
    image_path: str = None,
    image_data: bytes = None,
    temperature: float = 0.7,
    max_tokens: int = 2000
):
    """
    测试带图片的提示词优化接口

    Args:
        user_prompt: 用户输入的提示词
        image_path: 图片文件路径（可选）
        image_data: 图片字节数据（可选）
        temperature: 生成温度
        max_tokens: 最大token数
    """
    print("=" * 70)
    print("测试 /api/enhance_prompt 接口")
    print("=" * 70)
    print(f"原始提示词: {user_prompt}")
    print(f"温度: {temperature}")
    print(f"最大tokens: {max_tokens}")

    # 准备请求数据
    data = {
        'user_prompt': user_prompt,
        'temperature': temperature,
        'max_tokens': max_tokens
    }

    files = {}

    # 处理图片
    if image_path:
        print(f"使用图片文件: {image_path}")
        with open(image_path, 'rb') as f:
            files['image'] = (Path(image_path).name, f.read(), 'image/jpeg')
    elif image_data:
        print(f"使用生成的测试图片（大小: {len(image_data)} bytes）")
        files['image'] = ('test_image.jpg', image_data, 'image/jpeg')
    else:
        print("未提供图片")

    print("-" * 70)

    # 发送请求
    try:
        if files:
            response = requests.post(ENHANCE_PROMPT_URL, data=data, files=files)
        else:
            response = requests.post(ENHANCE_PROMPT_URL, data=data)

        response.raise_for_status()
        result = response.json()

        print("✅ 请求成功!")
        print("-" * 70)
        print(f"状态: {result.get('status')}")
        print(f"消息: {result.get('message')}")
        print("-" * 70)
        print("优化后的提示词:")
        print(result.get('enhanced_prompt'))
        print("=" * 70)

        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"响应状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
        return None


def test_with_contradictory_content():
    """
    测试1: 使用矛盾的内容
    图片显示"RED CAR"，但提示词说"蓝色汽车"
    如果API真的使用了图片，应该会提到红色；如果没用，应该会说蓝色
    """
    print("\n")
    print("🧪 测试 1: 矛盾内容测试")
    print("图片内容: 红色背景，写着 'RED CAR'")
    print("文字提示: 一辆蓝色汽车在公路上行驶")
    print()

    # 创建一个红色背景的图片，上面写着"RED CAR"
    image_data = create_test_image("RED CAR", color=(255, 0, 0))

    result = test_enhance_prompt_with_image(
        user_prompt="一辆蓝色汽车在公路上行驶",
        image_data=image_data
    )

    if result:
        enhanced = result.get('enhanced_prompt', '').lower()
        if 'red' in enhanced or '红' in enhanced or '红色' in enhanced:
            print("\n✅ 结果提到了红色 - 视觉模型成功识别图片内容！")
        elif 'blue' in enhanced or '蓝' in enhanced or '蓝色' in enhanced:
            print("\n⚠️  结果只提到蓝色 - 可能未使用图片内容")
        else:
            print("\n❓ 结果中没有明确的颜色信息")


def test_with_specific_image_content():
    """
    测试2: 使用具体图片内容
    图片显示"BEACH SUNSET"，提示词很简短
    如果API使用了图片，应该会生成关于海滩日落的内容
    """
    print("\n")
    print("🧪 测试 2: 具体图片内容测试")
    print("图片内容: 橙色背景，写着 'BEACH SUNSET'")
    print("文字提示: 一个美丽的场景")
    print()

    # 创建一个橙色背景的图片，上面写着"BEACH SUNSET"
    image_data = create_test_image("BEACH SUNSET", color=(255, 165, 0))

    result = test_enhance_prompt_with_image(
        user_prompt="一个美丽的场景",
        image_data=image_data
    )

    if result:
        enhanced = result.get('enhanced_prompt', '').lower()
        if 'beach' in enhanced or 'sunset' in enhanced or '海滩' in enhanced or '日落' in enhanced:
            print("\n✅ 结果提到了海滩或日落 - 视觉模型成功识别图片内容！")
        else:
            print("\n⚠️  结果没有提到海滩或日落 - 可能未使用图片内容")


def test_without_image():
    """
    测试3: 不上传图片作为对照组
    """
    print("\n")
    print("🧪 测试 3: 无图片对照测试")
    print("不上传图片，只使用文字提示")
    print()

    result = test_enhance_prompt_with_image(
        user_prompt="一辆蓝色汽车在公路上行驶",
        image_data=None
    )


def test_with_real_image(image_path: str):
    """
    测试4: 使用真实图片
    """
    print("\n")
    print("🧪 测试 4: 真实图片测试")
    print(f"使用图片文件: {image_path}")
    print()

    result = test_enhance_prompt_with_image(
        user_prompt="描述这张图片的内容",
        image_path=image_path
    )


def check_server_health():
    """检查服务器是否运行"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        response.raise_for_status()
        print("✅ 服务器运行正常")
        return True
    except Exception as e:
        print(f"❌ 服务器连接失败: {e}")
        print(f"请确保服务运行在 {API_BASE_URL}")
        return False


def main():
    parser = argparse.ArgumentParser(description="测试 enhance_prompt 接口")
    parser.add_argument('--image', type=str, help='可选：指定要测试的真实图片路径')
    parser.add_argument('--api-url', type=str, default="http://localhost:5014",
                       help='API服务地址（默认: http://localhost:5014）')
    args = parser.parse_args()

    # 更新 API URL
    global API_BASE_URL, ENHANCE_PROMPT_URL
    API_BASE_URL = args.api_url
    ENHANCE_PROMPT_URL = f"{API_BASE_URL}/api/enhance_prompt"

    print("=" * 70)
    print("enhance_prompt 接口测试工具")
    print("=" * 70)
    print(f"API 地址: {API_BASE_URL}")
    print()

    # 检查服务器
    if not check_server_health():
        return

    print()
    input("按 Enter 键开始测试...")

    # 运行自动测试
    test_with_contradictory_content()
    print("\n" + "=" * 70)
    input("按 Enter 键继续下一个测试...")

    test_with_specific_image_content()
    print("\n" + "=" * 70)
    input("按 Enter 键继续下一个测试...")

    test_without_image()

    # 如果提供了真实图片，也测试它
    if args.image:
        print("\n" + "=" * 70)
        input("按 Enter 键测试真实图片...")
        test_with_real_image(args.image)

    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)
    print("\n📋 测试总结:")
    print("当前使用 Moonshot AI 视觉模型，/api/enhance_prompt 接口支持图片分析。")
    print("视觉模型能够识别图片内容，并结合文字提示生成更准确的提示词。")
    print("\n✅ 支持的功能:")
    print("  • 图片内容识别（base64 编码上传）")
    print("  • 图文结合的提示词优化")
    print("  • 纯文本提示词优化（不上传图片时）")
    print("\n参考代码位置: wan22_i2v_14b_4.py:257-352")
    print("=" * 70)


if __name__ == "__main__":
    main()
