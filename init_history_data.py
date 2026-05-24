"""
初始化历史数据脚本
首次运行时执行，将所有指数的历史数据下载到本地CSV
"""

import sys
from history_data_manager import get_history_manager


def init_history_data():
    """初始化所有指数的历史数据"""
    print("=" * 60)
    print("历史数据初始化")
    print("=" * 60)
    print()

    manager = get_history_manager()

    # 更新所有数据
    manager.update_all_data()

    # 显示数据信息
    print()
    print("=" * 60)
    print("数据存储信息")
    print("=" * 60)

    info = manager.get_data_info()
    print(f"数据目录: {info['data_dir']}")
    print(f"文件数量: {info['total_files']}")
    print(f"总大小: {info['total_size_mb']} MB")
    print()

    for key, idx_info in info['indices'].items():
        print(f"{idx_info['name']} ({key}):")
        print(f"  记录数: {idx_info['records']}")
        print(f"  文件大小: {idx_info['size_mb']} MB")
        print(f"  数据范围: {idx_info['date_range'].get('start', 'N/A')} ~ {idx_info['date_range'].get('end', 'N/A')}")
        print(f"  最后更新: {idx_info['last_update']}")
        print()

    print("=" * 60)
    print("初始化完成！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        init_history_data()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
