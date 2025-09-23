# Ping Monitor Agent (Python)

環境変数で指定されたターゲットに対して継続的にpingを送信し、RTT・Jitter・PacketLossの統計情報を表示するPythonプログラムです。

## 機能

- ホスト名の自動解決
- 可変ping間隔（デフォルト100ms）
- リアルタイム統計表示：
  - 直近10秒
  - 直近1分
  - 直近5分
- RTT（平均・最小・最大）
- Jitter（RTTの標準偏差）
- パケットロス率
- **Verboseモード**: 個別パケット応答の詳細表示

## 使用方法

```bash
# 基本的な使用例
TARGET_HOST=google.com python ping_monitor.py

# ping間隔を指定（ミリ秒）
TARGET_HOST=8.8.8.8 PING_INTERVAL=50 python ping_monitor.py

# IPアドレスを直接指定
TARGET_HOST=1.1.1.1 python ping_monitor.py

# Verboseモード（個別パケット応答も表示）
TARGET_HOST=google.com python ping_monitor.py --verbose
TARGET_HOST=google.com python ping_monitor.py -v
```

### Verboseモード

`--verbose` または `-v` オプションを使用すると、統計情報に加えて個別パケットの応答状況もリアルタイムで表示されます。

```
[14:30:15] ✓ 8.8.8.8:  12.34ms - 64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=12.34 ms
[14:30:16] ✗ 8.8.8.8: FAILED - Ping failed (exit code: 1)
```

- `✓`: 成功したパケット（RTT値と詳細情報を表示）
- `✗`: 失敗したパケット（エラー理由を表示）
- タイムスタンプ付きで各パケットの状態を追跡

## 環境変数

- `TARGET_HOST`: 監視対象のホスト名またはIPアドレス（必須）
- `PING_INTERVAL`: ping送信間隔（ミリ秒、デフォルト: 100）

## 要件

- Python 3.6以上
- Unix系OS（macOS、Linux）
- `ping`コマンドが利用可能であること

## コマンドラインオプション

```bash
python ping_monitor.py [--verbose] [--help]
```

- `--verbose`, `-v`: 個別パケット応答の詳細表示を有効化
- `--help`, `-h`: ヘルプメッセージを表示

## 停止方法

`Ctrl+C`で安全に停止できます。
