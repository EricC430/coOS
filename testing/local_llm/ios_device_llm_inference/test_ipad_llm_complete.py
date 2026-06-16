import requests
import time

# 替換為您的 iPad IP 與 Port
IPAD_URL = "http://192.168.0.79:11434/api/chat"

# 我們測試系統要用的「意圖壓縮」情境
payload = {
    "model": "gemma-4-e4b-it-4bit",  # 使用我們剛剛查到的模型名稱
    "messages": [
        {
            "role": "user",
            "content": "What is the capital of France?",
            # "content": "你是一個行為分析系統。請根據以下日誌，只輸出一個代表其心理狀態的『詞彙』（例如：焦慮、逃避、冷靜），不要做任何多餘的解釋。\n\n日誌：連續切換 5 個檔案，刪除 20 行代碼，游標停留在錯誤行長達 3 分鐘。"
        }
    ],
    "stream": False  # 為了方便測試，我們先一次性接收完整回覆
}

print("正在將任務傳送至 iPad 進行邊緣運算...")
start_time = time.time()

try:
    response = requests.post(IPAD_URL, json=payload, timeout=60)
    response.raise_for_status() # 檢查是否有 HTTP 錯誤
    
    end_time = time.time()
    result = response.json()
    
    print("\n[SUCCESS] Inference Succeeded! iPad Response:")
    print(result)
    print(f"\n[TIME] Duration: {end_time - start_time:.2f} seconds")

except requests.exceptions.RequestException as e:
    print(f"\n[FAIL] Connection or inference failed: {e}")