import asyncio
import logging
import time

from runtime import ResearchRuntime
from utils import key_store


async def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    t0 = time.time()
    key_store.migrate_from_env()
    key_store.inject_to_environ()

    runtime = ResearchRuntime()
    await runtime.setup()
    print(f"[{time.time()-t0:.1f}s] 运行时就绪，工具：{[t.name for t in runtime.tools]}")

    topic = "新能源汽车市场"
    print(f"[{time.time()-t0:.1f}s] 开始调研：{topic}")
    try:
        result = await runtime.run(topic)
    finally:
        await runtime.close()
        print(f"[{time.time()-t0:.1f}s] 运行时已关闭")

    print("=" * 60)
    print("调研报告")
    print("=" * 60)
    print(result.get("draft", ""))
    print("-" * 60)
    print(f"检索词：{result.get('plan')}")
    print(f"审查评分：{result.get('review_score')}  改写轮次：{result.get('iteration')}")
    if result.get("error"):
        print("错误:", result["error"])


if __name__ == "__main__":
    asyncio.run(main())
