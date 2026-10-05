# 固定源码获取：仅联网准备，不执行

在解压后的 bundle 根目录操作。`retrieval-verification.json` 记录以下八个固定 URL 的历史 GET：均 HTTP 200，长度及 SHA-256 与锁定输入相同，七模块另核对 Git blob。本次离线入口已使用预置且哈希匹配的输入完成复演（见[运行摘要](execution-summary.json)），但未在复演时重新GET、下载Node或pull镜像；本页记录的是独立获取阶段。不可换成 main，不可忽略校验失败。

```bash
set -euo pipefail
mkdir snapshot
mkdir snapshot/src
curl --fail --location --proto '=https' --tlsv1.2 --retry 2 -o snapshot/src/admin-api.mjs https://raw.githubusercontent.com/openai/openai-cookbook/0eac1447d4e24d06e47c459ca5e98f248b9413cf/examples/chatgpt/daily_usage_limits/src/admin-api.mjs
curl --fail --location --proto '=https' --tlsv1.2 --retry 2 -o snapshot/src/controller.mjs https://raw.githubusercontent.com/openai/openai-cookbook/0eac1447d4e24d06e47c459ca5e98f248b9413cf/examples/chatgpt/daily_usage_limits/src/controller.mjs
curl --fail --location --proto '=https' --tlsv1.2 --retry 2 -o snapshot/src/enrollment.mjs https://raw.githubusercontent.com/openai/openai-cookbook/0eac1447d4e24d06e47c459ca5e98f248b9413cf/examples/chatgpt/daily_usage_limits/src/enrollment.mjs
curl --fail --location --proto '=https' --tlsv1.2 --retry 2 -o snapshot/src/policy.mjs https://raw.githubusercontent.com/openai/openai-cookbook/0eac1447d4e24d06e47c459ca5e98f248b9413cf/examples/chatgpt/daily_usage_limits/src/policy.mjs
curl --fail --location --proto '=https' --tlsv1.2 --retry 2 -o snapshot/src/renewal.mjs https://raw.githubusercontent.com/openai/openai-cookbook/0eac1447d4e24d06e47c459ca5e98f248b9413cf/examples/chatgpt/daily_usage_limits/src/renewal.mjs
curl --fail --location --proto '=https' --tlsv1.2 --retry 2 -o snapshot/src/selection.mjs https://raw.githubusercontent.com/openai/openai-cookbook/0eac1447d4e24d06e47c459ca5e98f248b9413cf/examples/chatgpt/daily_usage_limits/src/selection.mjs
curl --fail --location --proto '=https' --tlsv1.2 --retry 2 -o snapshot/src/synthetic.mjs https://raw.githubusercontent.com/openai/openai-cookbook/0eac1447d4e24d06e47c459ca5e98f248b9413cf/examples/chatgpt/daily_usage_limits/src/synthetic.mjs
curl --fail --location --proto '=https' --tlsv1.2 --retry 2 -o snapshot/LICENSE.upstream https://raw.githubusercontent.com/openai/openai-cookbook/0eac1447d4e24d06e47c459ca5e98f248b9413cf/LICENSE
(cd snapshot && sha256sum --check ../snapshot-SHA256SUMS)
```

这不是下载后执行脚本。`source-lock.json` 提供完整 commit、模块路径、URL、SHA-256、长度、Git blob 与静态 imports。离线 restager 再次验证全部字节后才建立 fresh 输出；额外 snapshot 文件不会被复制。下载中断或哈希不符应停止并重新获取对应文件，不应放宽校验。锁和校验清单本身须通过可信分发的 bundle 哈希核验；自洽哈希不是发布者身份签名。
