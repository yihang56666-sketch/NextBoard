# STM32 小型四旋翼无人机原理图连接表

**Project:** STM32 Small Quadrotor Drone
**Stage:** 07 - Schematic Link Map
**Date:** 2026-06-01

## 模块连接

### STM32G431

- VDD -> 3.3V
- VSS -> GND
- NRST -> 复位电路 + 调试口
- SWDIO/SWCLK -> 调试口
- SPI1 -> IMU
- UART1 -> 日志口
- UART2 -> 接收机或地面站
- TIM -> 4 路电调输出

### ICM-42688-P

- VDD -> 3.3V
- GND -> GND
- SCK/MISO/MOSI/CS -> STM32 SPI
- INT1 -> 中断输入

### BMP390（可选）

- VDD -> 3.3V
- GND -> GND
- SCK/MISO/MOSI/CS -> 共享 SPI 或独立 SPI

### 电源

- 电池输入 -> 保护/开关 -> 5V 降压
- 5V -> 3.3V LDO/DC-DC
- 3.3V -> MCU + 传感器

### 执行器

- MOTOR1..4 -> 4-in-1 ESC 信号

## 布局优先级

1. IMU 放板中心
2. 电源和开关节点远离 IMU
3. SWD 口靠板边
4. 传感器和 MCU 的去耦电容贴近引脚
