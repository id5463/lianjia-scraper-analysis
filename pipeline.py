"""
链家二手房：爬虫 + 分析 一体化管道

将 scrape_lianjia.py（数据获取）与 house_analysis.R（数据分析）
连接为一条完整的流水线，同时保留各自独立运行的能力。

──────────────────────────────────────────────────────────────────
三种模式：

  模式                        命令
  ─────────────────────────────────────────────────────────────
  ① 完整管道（默认）          python pipeline.py --city pds --count 50
  ② 仅爬取                   python pipeline.py --crawl-only --city bj --count 100
  ③ 仅分析                   python pipeline.py --analyze-only --csv pds_houses_10.csv
                              python pipeline.py --analyze-only --city pds   ← 自动找最新CSV

参数说明：
  --city        链家城市拼音缩写，如 pds / bj / sh / sz（默认 pds）
  --count       目标爬取条数（默认 50）
  --csv         指定CSV文件路径（仅分析模式手动指定）
  --crawl-only  只爬取，不分析
  --analyze-only 只分析已有CSV，不爬取
  --r-path      Rscript.exe 路径（默认自动查找）
"""

import os
import sys
import glob
import re
import subprocess
import argparse

# ── 脚本所在目录 ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ── 自动查找 Rscript.exe ────────────────────────────────────

def find_rscript():
    """尝试常见路径查找 Rscript.exe"""
    candidates = [
        os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'R', '*', 'bin', 'Rscript.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'R', '*', 'bin', 'Rscript.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'R', '*', 'bin', 'Rscript.exe'),
    ]
    for pattern in candidates:
        matches = sorted(glob.glob(pattern), reverse=True)
        if matches:
            return matches[0]

    # fallback: 在 PATH 中找
    try:
        result = subprocess.run(['where', 'Rscript'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except Exception:
        pass

    return None


# ── 获取城市最新CSV ─────────────────────────────────────────

def find_latest_csv(city):
    """根据城市拼音，查找最新生成的CSV文件"""
    base_name = f'{city}_houses'
    # 先找带编号的最新文件
    pattern = os.path.join(BASE_DIR, f'{base_name}_*.csv')
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if files:
        return files[0]
    # 再试试无编号的
    plain = os.path.join(BASE_DIR, f'{base_name}.csv')
    if os.path.exists(plain):
        # 检查是否有真实数据（不止表头）
        with open(plain, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        if len(lines) > 1:
            return plain
    return None


# ── 运行 R 分析 ─────────────────────────────────────────────

def run_analysis(csv_path, rscript_path):
    """调用 Rscript 执行 house_analysis.R"""
    if not os.path.isfile(csv_path):
        print(f'[错误] CSV 文件不存在: {csv_path}')
        return False

    r_path = rscript_path or find_rscript()
    if not r_path:
        print('[错误] 找不到 Rscript.exe。请通过 --r-path 手动指定路径。')
        print('  例如: --r-path "C:\\Program Files\\R\\R-4.6.0\\bin\\Rscript.exe"')
        return False

    analysis_r = os.path.join(BASE_DIR, 'house_analysis.R')
    if not os.path.isfile(analysis_r):
        print(f'[错误] 找不到 house_analysis.R: {analysis_r}')
        return False

    print(f'\n{"="*60}')
    print(f'  开始 R 分析')
    print(f'  CSV:     {csv_path}')
    print(f'  Rscript: {r_path}')
    print(f'  Script:  {analysis_r}')
    print(f'{"="*60}\n')

    result = subprocess.run(
        [r_path, analysis_r, csv_path],
        cwd=BASE_DIR,
        capture_output=False,
    )
    return result.returncode == 0


# ── 运行爬虫 ────────────────────────────────────────────────

def run_crawl(city, count):
    """调用 scrape_lianjia.py 的 crawl 函数"""
    print(f'\n{"="*60}')
    print(f'  开始爬取: city={city}, count={count}')
    print(f'{"="*60}\n')

    # 将爬虫模块所在目录加入 sys.path
    sys.path.insert(0, BASE_DIR)
    from scrape_lianjia import crawl
    result = crawl(city=city, count=count)
    return result  # {'csv_path': str, 'records': int}


# ── 主入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='链家二手房 爬虫+分析 一体化管道',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # 模式选择
    mode = parser.add_argument_group('模式选择（默认：完整管道）')
    mode.add_argument('--crawl-only', action='store_true',
                      help='仅爬取，不分析')
    mode.add_argument('--analyze-only', action='store_true',
                      help='仅分析已有CSV，不爬取')

    # 爬虫参数
    crawl_args = parser.add_argument_group('爬虫参数')
    crawl_args.add_argument('--city', default='pds',
                            help='链家城市拼音缩写，如 pds / bj / sh（默认 pds）')
    crawl_args.add_argument('--count', type=int, default=50,
                            help='目标爬取条数（默认 50）')

    # 分析参数
    analysis_args = parser.add_argument_group('分析参数')
    analysis_args.add_argument('--csv', default=None,
                               help='CSV 文件路径（仅分析模式可手动指定）')
    analysis_args.add_argument('--r-path', default=None,
                               help='Rscript.exe 路径，如 "C:\\Program Files\\R\\R-4.6.0\\bin\\Rscript.exe"')

    args = parser.parse_args()

    # ── 模式判断 ──
    if args.analyze_only and args.crawl_only:
        print('[错误] --crawl-only 和 --analyze-only 不能同时使用。')
        sys.exit(1)

    is_pipeline = not args.crawl_only and not args.analyze_only  # 默认：完整管道

    # ── 第一步：爬取 ──
    csv_path = None
    if args.analyze_only:
        # 仅分析模式：使用已有的 CSV
        if args.csv:
            csv_path = args.csv
            if not os.path.isfile(csv_path):
                print(f'[错误] 指定的 CSV 文件不存在: {csv_path}')
                sys.exit(1)
        else:
            csv_path = find_latest_csv(args.city)
            if not csv_path:
                print(f'[错误] 找不到 {args.city} 的最新CSV文件。')
                print('  请先运行爬虫，或通过 --csv 手动指定文件路径。')
                sys.exit(1)
            print(f'[自动匹配] 找到最新CSV: {csv_path}')

    elif args.crawl_only:
        # 仅爬取模式
        result = run_crawl(args.city, args.count)
        print(f'\n[完成] 爬取结束: {result["records"]} 条 → {result["csv_path"]}')
        return

    else:
        # 完整管道：爬取 → 分析
        result = run_crawl(args.city, args.count)
        csv_path = result['csv_path']
        print(f'\n[爬取完成] {result["records"]} 条记录，准备进入分析阶段...')

    # ── 第二步：分析 ──
    if csv_path:
        success = run_analysis(csv_path, args.r_path)
        if success:
            print(f'\n{"="*60}')
            print(f'  管道完成！')
            print(f'  数据: {csv_path}')
            # 分析输出的文件名
            base_name = os.path.splitext(os.path.basename(csv_path))[0]
            print(f'  报告: {os.path.join(BASE_DIR, base_name + "_analysis.txt")}')
            print(f'  图表: diagnostic_plots.png / actual_vs_predicted.png')
            print(f'        residual_histogram.png / area_vs_price.png')
            print(f'{"="*60}')
        else:
            print('[错误] 分析阶段失败。')
            sys.exit(1)


if __name__ == '__main__':
    main()
