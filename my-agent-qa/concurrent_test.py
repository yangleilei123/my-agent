import asyncio
import aiohttp
import time
import json
from datetime import datetime

async def make_request(session, url, question, session_id):
    """
    发送单个请求
    """
    data = {
        "question": question,
        "session_id": session_id
    }
    
    try:
        start_time = time.time()
        response = await session.post(url, json=data)
        end_time = time.time()
        
        response_data = await response.text()
        
        return {
            "status": response.status,
            "response": json.loads(response_data),
            "duration": end_time - start_time,
            "success": response.status == 200,
            "session_id": session_id
        }
    except Exception as e:
        return {
            "status": 500,
            "response": str(e),
            "duration": -1,
            "success": False,
            "session_id": session_id,
            "error": str(e)
        }

async def test_concurrent_requests(base_url, question, num_requests, concurrency_limit=10):
    """
    并发测试主函数
    """
    url = f"{base_url}/chat"
    semaphore = asyncio.Semaphore(concurrency_limit)  # 限制并发数
    
    async def limited_request(session, question, session_id):
        async with semaphore:
            return await make_request(session, url, question, session_id)
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        # 创建所有任务
        tasks = []
        for i in range(num_requests):
            session_id = f"test_session_{i}_{int(time.time() * 1000)}"
            task = limited_request(session, question, session_id)
            tasks.append(task)
        
        print(f"🚀 开始发送 {num_requests} 个并发请求...")
        print(f"⏰ 测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
        
        start_total = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_total = time.time()
        
        # 统计结果
        successful_requests = 0
        failed_requests = 0
        total_duration = 0
        max_duration = 0
        min_duration = float('inf')
        
        print("\n📋 请求详情:")
        for i, result in enumerate(results):
            if isinstance(result, dict):
                duration = result['duration']
                success = result['success']
                
                if success:
                    successful_requests += 1
                    total_duration += duration
                    max_duration = max(max_duration, duration)
                    min_duration = min(min_duration, duration)
                    
                    answer_preview = result['response'].get('answer', '')[:100] + "..."
                    print(f"  ✓ 请求 {i+1:2d} | Session: {result['session_id']} | "
                          f"耗时: {duration:.2f}s | 状态: {result['status']}")
                    print(f"           | 答案预览: {answer_preview}")
                else:
                    failed_requests += 1
                    print(f"  ✗ 请求 {i+1:2d} | Session: {result['session_id']} | "
                          f"耗时: {duration:.2f}s | 状态: {result['status']}")
                    if 'error' in result:
                        print(f"           | 错误: {result['error']}")
            else:
                failed_requests += 1
                print(f"  ✗ 请求 {i+1:2d} | 异常: {str(result)}")
        
        print("-" * 80)
        print("📊 测试统计:")
        print(f"  总请求数: {num_requests}")
        print(f"  成功请求数: {successful_requests}")
        print(f"  失败请求数: {failed_requests}")
        print(f"  成功率: {(successful_requests/num_requests)*100:.2f}%")
        print(f"  总耗时: {end_total - start_total:.2f} 秒")
        print(f"  平均响应时间: {total_duration/successful_requests:.2f} 秒" if successful_requests > 0 else "  平均响应时间: N/A")
        print(f"  最长响应时间: {max_duration:.2f} 秒" if max_duration != float('inf') else "  最长响应时间: N/A")
        print(f"  最短响应时间: {min_duration:.2f} 秒" if min_duration != float('inf') else "  最短响应时间: N/A")
        print(f"  RPS (每秒请求数): {num_requests/(end_total - start_total):.2f}")
        print(f"  测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def run_tests():
    """
    运行多种并发测试
    """
    base_url = "http://localhost:8000"
    question = "杨雷雷是谁"
    
    test_configs = [
        {"num_requests": 5, "concurrency_limit": 2, "name": "小规模测试 (5个请求, 2并发)"},
        {"num_requests": 10, "concurrency_limit": 5, "name": "中等规模测试 (10个请求, 5并发)"},
        {"num_requests": 20, "concurrency_limit": 10, "name": "较大规模测试 (20个请求, 10并发)"},
        {"num_requests": 30, "concurrency_limit": 15, "name": "压力测试 (30个请求, 15并发)"},
    ]
    
    for config in test_configs:
        print(f"\n{'='*80}")
        print(f"🧪 {config['name']}")
        print(f"{'='*80}")
        
        asyncio.run(test_concurrent_requests(
            base_url, 
            question, 
            config['num_requests'], 
            config['concurrency_limit']
        ))
        
        # 在测试之间暂停一下
        print(f"\n⏳ 等待 2 秒后开始下一个测试...")
        time.sleep(2)

def run_single_test():
    """
    运行单个测试
    """
    base_url = "http://localhost:8000"
    question = "杨雷雷是谁"
    
    print("🧪 单个并发测试")
    print("="*80)
    
    asyncio.run(test_concurrent_requests(base_url, question, 4, 5))

if __name__ == "__main__":
    print("🧪 Agent 并发测试工具")
    print("📋 测试问题: '杨雷雷是谁'")
    print("🌐 目标地址: http://localhost:8000")
    print()
    
    choice = input("选择测试模式 - 1: 单个测试, 2: 完整测试套件 (默认1): ").strip()
    
    if choice == "2":
        run_tests()
    else:
        run_single_test()