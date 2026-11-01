# data/raw

原始数据目录。`online_retail.xlsx`（约 23 MB）**未纳入版本库**，运行下列任一方式即可获得：

```bash
python scripts/01_load.py          # 自动从 UCI 官方地址下载并校验
```

或手动下载后放置为本目录下的 `online_retail.xlsx`：

- 官方地址：https://archive.ics.uci.edu/static/public/352/online+retail.zip
- 解压后得到 `Online Retail.xlsx`，重命名并放入本目录

下载完成后，`source_meta.json` 会记录：下载方式、实际 URL、字节数、SHA-256、获取时间、
许可信息与数据规模。该文件是数据来源合规的可审计凭证。
