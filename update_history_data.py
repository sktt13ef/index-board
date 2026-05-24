"""
更新历史数据脚本
用于定时更新本地CSV文件中的历史数据
"""

import sys
import argparse
from datetime import datetime
from history_data_manager import get_history_manager


def update_history_data(force: bool = False):
    """
    更新历史数据

    Args:
        force: 强制更新所有数据，忽略有效期检查
    """
    print("=" * 60)
    print(f"历史数据更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    manager = get_history_manager()

    if force:
        print("强制更新模式：更新所有数据")
        print()
        manager.update_all_data()
    else:
        # 检查哪些数据需要更新
        print("检查数据更新...")
        print()

        need_update = []
        for key in manager.INDICES:
            if not manager._is_data_valid(key):
                need_update.append(key)

        if not need_update:
            print("所有数据都在有效期内，无需更新")
            return

        print(f"需要更新的指数: {len(need_update)} 个")
        print()

        for key in need_update:
            try:
                name = manager.INDICES[key]['name']
                print(f"更新 {name}...")
                data = manager.fetch_from_remote(key)
                if data:
                    manager.save_local_data(key, data)
            except Exception as e:
                print(f"  更新失败: {e}")

    # 显示数据信息
    print()
    print("=" * 60)
    print("更新完成 - 数据存储信息")
    print("=" * 60)

    info = manager.get_data_info()
    print(f"总文件数: {info['total_files']}")
    print(f"总大小: {info['total_size_mb']} MB")
    print()

    for key, idx_info in info['indices'].items():
        print(f"{idx_info['name']}: {idx_info['records']} 条记录, {idx_info['size_mb']} MB")

    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='更新历史数据')
    parser.add_argument('--force', '-f', action='store_true',
                        help='强制更新所有数据，忽略有效期检查')
    parser.add_argument('--info', '-i', action='store_true',
                        help='仅显示数据信息，不更新')

    args = parser.parse_args()

    if args.info:
        # 仅显示信息
        manager = get_history_manager()
        info = manager.get_data_info()
        print("=" * 60)
        print("历史数据存储信息")
        print("=" * 60)
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
    else:
        # 执行更新
        update_history_data(force=args.force)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
