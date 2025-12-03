# CSV 日志说明 - 它不会写入 QuickBooks

## ⚠️ 重要澄清

**CSV 日志 (`logs/quotes_log.csv`) 不会写入 QuickBooks！**

CSV 日志是一个**本地记录文件**，用来记录：
- 哪些报价被处理了
- 处理结果（成功/失败）
- QuickBooks 返回的 ID
- 错误信息

**它只是记录，不会发送数据到 QuickBooks。**

---

## 📊 CSV 日志的流程

### 1. 哪个文件写入 CSV？

**文件**: `cli_push_estimate.py`  
**函数**: `append_log()`

### 2. CSV 日志写在哪里？

**位置**: `logs/quotes_log.csv` (本地文件系统)

**路径**: 在项目根目录下的 `logs/` 文件夹

### 3. CSV 日志包含什么？

```csv
timestamp,reference,customer_name,items_count,subtotal,currency,status,pdf_path,qbo_estimate_id,error
2025-01-15T10:30:00Z,GT-001,John Doe,3,450.00,CAD,created,Quotes/Estimate_GT-001.pdf,123,
2025-01-15T10:35:00Z,GT-002,Jane Smith,2,300.00,CAD,failed,,,QuickBooks API Error: Invalid customer
```

**字段说明**:
- `timestamp` - 处理时间
- `reference` - 报价编号
- `customer_name` - 客户名称
- `items_count` - 项目数量
- `subtotal` - 小计金额
- `currency` - 货币
- `status` - 状态 (created/failed)
- `pdf_path` - PDF 文件路径
- `qbo_estimate_id` - QuickBooks 返回的 Estimate ID
- `error` - 错误信息（如果有）

---

## 🔄 完整的数据流程

### 数据如何到达 QuickBooks？

```
1. 用户输入/Excel
   ↓
2. create_estimate.py 或 api_server.py (Layer 5)
   ↓
3. cli_push_estimate.py (Layer 4) - 调用 append_log() 写入 CSV
   ↓
4. mapping.py (Layer 3) - 转换数据格式
   ↓
5. quickbooks_client.py (Layer 2) - 实际发送到 QuickBooks
   ↓
6. oauth.py (Layer 1) - 提供认证
   ↓
7. QuickBooks API (外部)
```

### 关键点：

1. **`cli_push_estimate.py`** 负责：
   - 调用 `quickbooks_client.py` 发送数据到 QuickBooks
   - 调用 `append_log()` 记录到 CSV（本地日志）

2. **`quickbooks_client.py`** 负责：
   - 实际发送 HTTP 请求到 QuickBooks API
   - 这是**唯一**写入 QuickBooks 的文件

3. **`append_log()`** 负责：
   - 只写入本地 CSV 文件
   - **不**发送任何数据到 QuickBooks

---

## 📝 append_log() 函数详解

**位置**: `cli_push_estimate.py` 第 42-61 行

```python
def append_log(reference, customer, items_count, subtotal, currency, 
               status, pdf_path, error="", qbo_id=""):
    """Appends a row to the CSV log file"""
    log_path = pathlib.Path("logs/quotes_log.csv")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 检查文件是否存在
    new_file = not log_path.exists() or log_path.stat().st_size == 0
    
    # 打开文件追加模式
    with log_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        
        # 如果是新文件，写入表头
        if new_file:
            w.writerow([
                "timestamp", "reference", "customer_name", "items_count",
                "subtotal", "currency", "status", "pdf_path", 
                "qbo_estimate_id", "error"
            ])
        
        # 写入数据行
        w.writerow([
            utc_now(), reference, customer, items_count,
            f"{subtotal:.2f}", currency, status, pdf_path, 
            qbo_id, error[:200]
        ])
```

**这个函数做什么**:
- ✅ 创建 `logs/` 文件夹（如果不存在）
- ✅ 创建 `quotes_log.csv` 文件（如果不存在）
- ✅ 写入表头（如果是新文件）
- ✅ 追加一行日志数据

**这个函数不做什么**:
- ❌ 不发送数据到 QuickBooks
- ❌ 不调用任何 API
- ❌ 不连接网络

---

## 🎯 什么时候调用 append_log()？

在 `cli_push_estimate.py` 的 `process_quickbooks()` 函数中：

### 成功时（第 219 行）:
```python
# Step 5: Log success
append_log(doc_number, customer_name, len(items), total_amt, currency,
           "created", str(pdf_path), qbo_id=estimate_id)
```

### 失败时（第 249 行）:
```python
# Log failure
append_log(reference, customer_name, len(items), subtotal, currency,
           "failed", "", error=error_msg)
```

### 异常时（第 264 行）:
```python
# Log failure
append_log(reference, customer_name, len(items), subtotal, currency,
           "failed", "", error=error_msg)
```

---

## 🔍 实际发送到 QuickBooks 的文件

**文件**: `quickbooks_client.py`

**关键函数**:
- `create_estimate(estimate_data)` - 创建 Estimate
- `get_or_create_customer(customer_data)` - 创建/获取客户
- `_make_request()` - 发送 HTTP 请求

**这些函数**:
- ✅ 实际发送 HTTP POST 请求到 QuickBooks API
- ✅ 接收 QuickBooks 的响应
- ✅ 返回 QuickBooks 返回的 ID

---

## 📊 数据流向图

```
┌─────────────────────────────────────────┐
│  cli_push_estimate.py                  │
│                                         │
│  1. 调用 quickbooks_client.py           │
│     ↓                                   │
│  2. 发送数据到 QuickBooks ✅            │
│     ↓                                   │
│  3. 收到 QuickBooks 返回的 ID           │
│     ↓                                   │
│  4. 调用 append_log()                   │
│     ↓                                   │
│  5. 写入 logs/quotes_log.csv ✅         │
│     (本地文件，不发送到 QuickBooks)      │
└─────────────────────────────────────────┘
```

---

## 🎓 总结

| 文件 | 功能 | 是否写入 QuickBooks |
|------|------|---------------------|
| `cli_push_estimate.py` | 调用其他模块，记录日志 | ❌ 不直接写入 |
| `append_log()` | 写入 CSV 日志 | ❌ 只写本地文件 |
| `quickbooks_client.py` | 发送 HTTP 请求 | ✅ **这是唯一写入 QuickBooks 的文件** |
| `logs/quotes_log.csv` | 本地日志文件 | ❌ 只是记录 |

**关键理解**:
- CSV 日志 = **本地记录**（就像记账本）
- QuickBooks = **云端数据库**（实际存储数据的地方）
- `quickbooks_client.py` = **桥梁**（连接本地和 QuickBooks）

CSV 日志只是用来**追踪**哪些数据已经发送到 QuickBooks，但它本身**不会**发送数据到 QuickBooks。

