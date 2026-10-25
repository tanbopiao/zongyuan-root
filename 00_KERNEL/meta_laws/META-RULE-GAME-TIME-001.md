# 元法则 META-RULE-GAME-TIME-001
# 游戏使用时间限制规则

## 规则内容
所有游戏进程（网易游戏、Minecraft等），只允许在以下时间段运行：
- **允许时间段：每天 21:00 - 22:00**
- **禁止时间段：其他所有时间**

## 强制执行方式
1. 每小时自动运行 game_time_limiter.ps1
2. 非允许时间段自动关闭所有游戏进程
3. 所有操作记录到日志

## 限制的游戏进程
- Minecraft.Windows
- WPFLauncher
- FeverGamesWeb
- FeverGamesInstaller
- FeverGamesService

## 例外情况
- 用户明确手动启动游戏时，当天可延长使用
- 系统维护期间暂停限制

## 生效时间
永久生效，全域锁档

Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT
