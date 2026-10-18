import argparse
import base64
import csv
import json
import os
from html import escape
from pathlib import Path


def relpath(path, start):
    href = os.path.relpath(Path(path).resolve(), start=Path(start).resolve().parent)
    return href.replace(os.sep, "/")


def image_data_uri(path):
    suffix = Path(path).suffix.lower()
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def figure_specs(sample):
    base = Path(sample)
    return [
        (
            "reads",
            "Read length",
            "序列长度分布",
            base / "reads_length" / "length_hist.png",
            "Short read enrichment is a common feature of degraded ancient DNA. The distribution helps assess read merging efficiency and downstream assembly suitability.",
            "短片段富集是降解古 DNA 的常见特征。该分布可用于评估 reads 合并效果，以及后续组装分析的适用性。",
        ),
        (
            "ani",
            "ANI histogram",
            "ANI 分布",
            base / "ani" / "ani_hist.png",
            "ANI values summarize the similarity between recovered MAGs and their closest GTDB references. High-ANI bins support species-level assignments, while missing or low values indicate more distant references.",
            "ANI 反映 recovered MAG 与最接近 GTDB 参考基因组之间的相似性。较高 ANI 支持物种水平注释，缺失或较低 ANI 则提示参考关系较远。",
        ),
        (
            "pydamage",
            "PyDamage contig stats",
            "PyDamage contig 统计",
            base / "contig_stats" / "pydamage_props.png",
            "This panel summarizes the fraction of contigs passing the configured PyDamage accuracy and q-value thresholds. Higher significant fractions provide additional support for ancient-like damage patterns.",
            "该图汇总满足 PyDamage accuracy 与 q-value 阈值的 contig 比例。显著比例越高，越支持样本中存在 ancient-like 损伤模式。",
        ),
        (
            "phylum",
            "Phylum rose chart",
            "门水平玫瑰图",
            base / "rose" / "phylum_rose.png",
            "The rose chart provides a compact view of MAG taxonomic composition at phylum level. Larger sectors indicate phyla represented by more classified MAGs in the sample.",
            "玫瑰图用于概览 MAG 在门水平的分类组成。扇区越大，表示该样本中该门对应的已分类 MAG 数量越多。",
        ),
        (
            "genus",
            "Genus rose chart",
            "属水平玫瑰图",
            base / "rose" / "genus_rose.png",
            "Genus-level composition provides a more detailed view of the recovered MAG community while retaining low-abundance genera in an Others category.",
            "属水平组成进一步展示 recovered MAG 群落结构，低丰度属会合并到 Others 类别。",
        ),
        (
            "species",
            "Top species rose chart",
            "主要物种玫瑰图",
            base / "rose" / "species_topn_rose.png",
            "The most represented species-level assignments are shown explicitly; remaining assignments are grouped as Others.",
            "丰度最高的物种水平分类会单独展示，其余分类合并到 Others。",
        ),
        (
            "checkm2",
            "CheckM2 quality",
            "CheckM2 质量评估",
            base / "checkm2" / "checkm2_scatter.png",
            "Completeness and contamination are plotted as proxy quality classes. These labels do not evaluate the rRNA/tRNA requirements of the full MIMAG high-quality standard.",
            "该图依据完整度和污染度给出代理质量分级，并未评估完整 MIMAG 高质量标准中的 rRNA/tRNA 要求。",
        ),
        (
            "gunc",
            "GUNC CSS",
            "GUNC CSS",
            base / "gunc" / "gunc_css_box_jitter.png",
            "GUNC clade separation scores highlight potential chimerism or taxonomic inconsistency. Lower CSS values are generally more consistent with cleaner MAG assignments.",
            "GUNC clade separation score 用于提示潜在嵌合或分类不一致。较低 CSS 通常更符合较干净的 MAG 分类结果。",
        ),
    ]


def slugify(value):
    slug = "".join(char.lower() if char.isalnum() else "-" for char in str(value))
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "item"


def read_summary_rows(path):
    with Path(path).open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_alpha_rows(paths):
    rows = []
    for path in paths:
        with Path(path).open("r", encoding="utf-8", errors="replace", newline="") as handle:
            rows.extend(csv.DictReader(handle, delimiter="\t"))
    return rows


def report_settings(config):
    params = config.get("params", {})
    return {
        "Preprocessing": params.get("preprocess_method", "fastp"),
        "Minimum contig length": params.get("min_contig_len", 500),
        "Ancient-contig-only binning": bool(params.get("use_ancient_contigs", False)),
        "PyDamage maximum q-value": params.get("pydamage_qvalue_max", 0.05),
        "PyDamage minimum predicted accuracy": params.get("pydamage_predicted_accuracy_min", 0.5),
        "Bin refinement": bool(params.get("enable_bin_refinement", False)),
        "Selected unrefined binner": params.get("unrefined_binner", "metabat2"),
        "CheckM2": bool(params.get("enable_checkm2", True)),
        "GUNC": bool(params.get("enable_gunc", True)),
        "GTDB-Tk": bool(params.get("enable_gtdbtk", True)),
        "Prokka": bool(params.get("enable_prokka", True)),
        "eggNOG-mapper": bool(params.get("enable_eggnog", False)),
        "ABRicate": bool(params.get("enable_abricate", False)),
        "RGI": bool(params.get("enable_rgi", False)),
        "antiSMASH": bool(params.get("enable_antismash", False)),
        "Variant calling": bool(params.get("enable_variants", False)),
        "MAG quality label": "Completeness/contamination proxy; full MIMAG criteria not evaluated",
    }


def summarize_mag_rows(rows):
    by_sample = {}
    by_quality = {}
    for row in rows:
        sample = str(row.get("Sample_ID") or "Unknown")
        quality = str(row.get("Quality") or "Unknown")
        by_sample[sample] = by_sample.get(sample, 0) + 1
        by_quality[quality] = by_quality.get(quality, 0) + 1
    return {
        "mag_count": len(rows),
        "by_sample": dict(sorted(by_sample.items())),
        "by_quality": dict(sorted(by_quality.items())),
    }


def _format_index(value, digits=3):
    """Display a diversity index at a readable precision.

    The TSV keeps full precision for downstream analysis; the report shows
    three decimals, which is beyond what a Shannon index can resolve from a
    few dozen MAGs anyway. Non-numeric values are shown unchanged.
    """
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value if value is not None else "")


def _overview_html(summary, settings, alpha_rows):
    sample_rows = "".join(
        f"<tr><th>{escape(name)}</th><td>{count}</td></tr>"
        for name, count in summary["by_sample"].items()
    ) or '<tr><td colspan="2">No MAG rows were produced.</td></tr>'
    quality_rows = "".join(
        f"<tr><th>{escape(name)}</th><td>{count}</td></tr>"
        for name, count in summary["by_quality"].items()
    ) or '<tr><td colspan="2">No quality classifications were produced.</td></tr>'
    setting_rows = "".join(
        f"<tr><th>{escape(str(name))}</th><td>{escape(str(value))}</td></tr>"
        for name, value in settings.items()
    )
    alpha_body = "".join(
        "<tr>"
        f"<td>{escape(str(row.get('sample', '')))}</td>"
        f"<td>{escape(str(row.get('rank', '')))}</td>"
        f"<td class=\"numeric\">{escape(_format_index(row.get('shannon_index', '')))}</td>"
        f"<td class=\"numeric\">{escape(str(row.get('observed_taxa', '')))}</td>"
        f"<td class=\"numeric\">{escape(str(row.get('total_bins', '')))}</td>"
        "</tr>"
        for row in alpha_rows
    )
    alpha_table = ""
    if alpha_body:
        alpha_table = "".join(
            [
                '<h3 data-i18n-en="Taxonomic alpha diversity" data-i18n-zh="分类学 Alpha 多样性">Taxonomic alpha diversity</h3>',
                '<div class="table-wrap"><table><thead><tr>',
                '<th>Sample</th><th>Rank</th><th class="numeric">Shannon index</th>'
                '<th class="numeric">Observed taxa</th><th class="numeric">MAGs</th>',
                f"</tr></thead><tbody>{alpha_body}</tbody></table></div>",
            ]
        )
    return "\n".join(
        [
            '<section class="overview" id="overview">',
            '<h2 data-i18n-en="Run overview" data-i18n-zh="运行概览">Run overview</h2>',
            f'<p class="summary-total"><strong>{summary["mag_count"]}</strong> MAG records in the merged summary.</p>',
            '<div class="overview-grid">',
            f'<div><h3>MAGs by sample</h3><table>{sample_rows}</table></div>',
            f'<div><h3>MAGs by quality proxy</h3><table>{quality_rows}</table></div>',
            '</div>',
            '<h3>Analysis settings</h3>',
            f'<div class="table-wrap"><table>{setting_rows}</table></div>',
            alpha_table,
            '</section>',
        ]
    )


def build_report_html(
    visualization_dir,
    samples,
    output,
    embed_images=False,
    enabled_figure_keys=None,
    summary_rows=None,
    settings=None,
    alpha_rows=None,
):
    visualization_dir = Path(visualization_dir)
    output = Path(output)
    enabled = set(enabled_figure_keys or [])
    summary = summarize_mag_rows(summary_rows or [])
    settings = settings or {}
    alpha_rows = alpha_rows or []
    sections = []
    nav_sections = []
    for sample in samples:
        sample_slug = slugify(sample)
        nav_links = []
        cards = []
        for figure_key, title_en, title_zh, relative_image, caption_en, caption_zh in figure_specs(sample):
            if enabled and figure_key not in enabled:
                continue
            figure_id = f"{sample_slug}-{slugify(title_en)}"
            nav_links.append(
                (
                    f'<a href="#{figure_id}" data-i18n-en="{escape(title_en)}" '
                    f'data-i18n-zh="{escape(title_zh)}">{escape(title_en)}</a>'
                )
            )
            image_path = visualization_dir / relative_image
            if not image_path.exists():
                cards.append(
                    "\n".join(
                        [
                            f'<article class="card missing" id="{figure_id}">',
                            (
                                f'<h3 data-i18n-en="{escape(title_en)}" '
                                f'data-i18n-zh="{escape(title_zh)}">{escape(title_en)}</h3>'
                            ),
                            '<p data-i18n-en="Missing output" data-i18n-zh="缺少输出">Missing output</p>',
                            (
                                f'<p class="caption" data-i18n-en="{escape(caption_en)}" '
                                f'data-i18n-zh="{escape(caption_zh)}">{escape(caption_en)}</p>'
                            ),
                            "</article>",
                        ]
                    )
                )
                continue

            if embed_images:
                image_href = escape(image_data_uri(image_path))
            else:
                image_href = escape(str(relpath(image_path, output)))
            cards.append(
                "\n".join(
                    [
                        f'<article class="card" id="{figure_id}">',
                        (
                            f'<h3 data-i18n-en="{escape(title_en)}" '
                            f'data-i18n-zh="{escape(title_zh)}">{escape(title_en)}</h3>'
                        ),
                        (
                            '<button class="image-button" type="button" '
                            f'aria-label="Open {escape(title_en)}">'
                            f'<img class="zoomable" src="{image_href}" alt="{escape(title_en)}" '
                            f'data-title="{escape(title_en)}" data-title-en="{escape(title_en)}" '
                            f'data-title-zh="{escape(title_zh)}">'
                            "</button>"
                        ),
                        (
                            f'<p class="caption" data-i18n-en="{escape(caption_en)}" '
                            f'data-i18n-zh="{escape(caption_zh)}">{escape(caption_en)}</p>'
                        ),
                        "</article>",
                    ]
                )
            )

        nav_sections.append(
            "\n".join(
                [
                    '<div class="nav-sample">',
                    f'<a class="nav-sample-link" href="#sample-{sample_slug}">{escape(sample)}</a>',
                    '<div class="nav-figures">',
                    *nav_links,
                    "</div>",
                    "</div>",
                ]
            )
        )
        sections.append(
            "\n".join(
                [
                    f'<section class="sample" id="sample-{sample_slug}">',
                    f"<h2>{escape(sample)}</h2>",
                    '<div class="figure-stack">',
                    *cards,
                    "</div>",
                    "</section>",
                ]
            )
        )

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>APPAM Visualization Report</title>",
            "<style>",
            ":root{--paper:#f5f1e8;--surface:#fffdf8;--ink:#202323;--muted:#66706a;--line:#ded6c7;--nav:#17201e;--nav-soft:#21302c;--nav-muted:#b9c5bd;--accent:#1f8a70;--accent-warm:#b66b3f;--shadow:0 18px 50px rgba(31,38,35,.10)}",
            "*{box-sizing:border-box}",
            "body{font-family:'Avenir Next','Gill Sans','Trebuchet MS',sans-serif;margin:0;color:var(--ink);background:var(--paper);background-image:linear-gradient(rgba(32,35,35,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(32,35,35,.035) 1px,transparent 1px);background-size:32px 32px;overflow-x:hidden}",
            "html{scroll-behavior:smooth}",
            "a:focus-visible,button:focus-visible{outline:3px solid rgba(31,138,112,.35);outline-offset:3px}",
            "header{margin-left:280px;padding:32px clamp(20px,4vw,56px) 24px;background:linear-gradient(180deg,rgba(255,253,248,.96),rgba(255,253,248,.72));border-bottom:1px solid var(--line);display:flex;align-items:flex-end;justify-content:space-between;gap:20px}",
            "header h1{font-family:Georgia,'Iowan Old Style',serif;font-weight:600;font-size:clamp(30px,4vw,52px);line-height:.96;margin:0;letter-spacing:0;color:var(--ink)}",
            ".eyebrow{display:inline-flex;align-items:center;gap:8px;margin:0 0 12px;color:var(--accent-warm);font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.16em}",
            ".eyebrow::before{content:'';width:28px;height:1px;background:var(--accent-warm);display:inline-block}",
            ".language-toggle{display:inline-flex;gap:4px;padding:4px;border:1px solid var(--line);border-radius:999px;background:rgba(255,253,248,.72);white-space:nowrap}",
            ".lang-button{border:0;border-radius:999px;background:transparent;color:var(--muted);font-weight:700;font-size:12px;padding:7px 10px;cursor:pointer}",
            ".lang-button.active{background:var(--nav);color:white}",
            ".layout{display:flex;align-items:flex-start}",
            ".sidebar{position:fixed;top:0;left:0;bottom:0;width:244px;overflow:auto;background:var(--nav);border-right:1px solid rgba(255,255,255,.08);padding:24px 18px;color:white}",
            ".sidebar h2{font-size:12px;margin:0 0 20px;color:var(--nav-muted);text-transform:uppercase;letter-spacing:.14em}",
            ".nav-sample{margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid rgba(255,255,255,.08)}",
            ".nav-sample-link{display:block;font-weight:700;color:#fff;text-decoration:none;margin-bottom:10px;font-size:15px}",
            ".nav-figures{display:flex;flex-direction:column;gap:4px}",
            ".nav-figures a{color:var(--nav-muted);text-decoration:none;font-size:13px;line-height:1.25;padding:6px 8px 6px 12px;border-left:2px solid transparent;border-radius:0 6px 6px 0}",
            ".nav-figures a:hover,.nav-figures a:focus-visible{color:#fff;background:var(--nav-soft);border-left-color:var(--accent)}",
            ".nav-sample-link:hover{color:#fff;text-decoration:underline;text-decoration-color:var(--accent);text-underline-offset:4px}",
            "main{margin-left:280px;padding:32px clamp(20px,4vw,56px) 56px;max-width:1120px;width:calc(100% - 320px)}",
            ".sample{margin-bottom:42px;scroll-margin-top:28px}",
            ".sample h2{font-family:Georgia,'Iowan Old Style',serif;font-size:clamp(24px,3vw,34px);font-weight:600;margin:0 0 18px;color:var(--ink)}",
            ".figure-stack{display:flex;flex-direction:column;gap:20px;counter-reset:figure}",
            ".card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:16px;scroll-margin-top:28px;overflow:hidden;box-shadow:var(--shadow)}",
            ".card h3{font-size:15px;margin:0 0 14px;display:flex;align-items:center;gap:10px;color:var(--ink);letter-spacing:0}",
            ".card h3::before{counter-increment:figure;content:'Fig. ' counter(figure,decimal-leading-zero);font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:white;background:var(--accent);border-radius:999px;padding:4px 8px}",
            ".image-button{border:0;background:#f9f5ed;padding:10px;margin:0 auto;width:100%;max-width:min(860px,100%);display:block;cursor:zoom-in;border-radius:6px}",
            ".card img{width:100%;max-width:100%;height:auto;display:block;border-radius:4px}",
            ".caption{max-width:860px;margin:12px auto 0;color:var(--muted);font-size:14px;line-height:1.55}",
            ".missing{color:var(--muted);background:rgba(255,253,248,.72);border-style:dashed;box-shadow:none}",
            ".missing p{margin:0;color:var(--muted)}",
            ".missing .caption{margin-top:8px}",
            ".overview{margin-bottom:42px;scroll-margin-top:28px}.overview h2{font-family:Georgia,'Iowan Old Style',serif;font-size:30px;margin:0 0 18px}.overview h3{font-size:15px;margin:20px 0 8px}.overview-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.overview table{width:100%;border-collapse:collapse}.overview th,.overview td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left}.overview th{font-weight:600}.summary-total{color:var(--muted)}.summary-total strong{font-size:26px;color:var(--ink);margin-right:6px}.table-wrap{overflow:auto}.overview .numeric{font-variant-numeric:tabular-nums;text-align:right}",
            ".modal{position:fixed;inset:0;background:rgba(15,20,18,.88);display:none;align-items:center;justify-content:center;padding:28px;z-index:1000}",
            ".modal.open{display:flex}",
            ".modal-content{max-width:min(96vw,1400px);max-height:90vh}",
            ".modal-content img{max-width:100%;max-height:82vh;display:block;background:var(--surface);border-radius:6px}",
            ".modal-title{color:white;font-size:18px;margin:0 0 12px}",
            ".modal-close{position:absolute;top:16px;right:18px;border:1px solid rgba(255,255,255,.28);background:var(--surface);color:var(--ink);border-radius:6px;padding:8px 12px;cursor:pointer}",
            "@media(prefers-reduced-motion:no-preference){.card{transition:transform .18s ease,box-shadow .18s ease}.card:hover{transform:translateY(-2px);box-shadow:0 22px 58px rgba(31,38,35,.14)}.image-button{transition:background .18s ease}.image-button:hover{background:#f1eadf}}",
            "@media(max-width:860px){header{margin-left:0;padding:22px 18px;align-items:flex-start;flex-direction:column}.layout{display:block}.sidebar{position:sticky;top:0;z-index:20;width:auto;max-height:40vh;border-right:0;border-bottom:1px solid rgba(255,255,255,.12);padding:16px 14px}.nav-sample{margin-bottom:14px;padding-bottom:12px}.nav-figures{flex-direction:row;flex-wrap:wrap}.nav-figures a{padding:5px 8px;border-left:0;border-bottom:2px solid transparent;border-radius:6px}.nav-figures a:hover,.nav-figures a:focus-visible{border-left-color:transparent;border-bottom-color:var(--accent)}main{margin-left:0;width:auto;max-width:none;padding:22px 16px 36px}.image-button{max-width:100%;padding:6px}.modal{padding:16px}.overview-grid{grid-template-columns:1fr}}",
            "</style>",
            "</head>",
            "<body>",
            "<header>",
            '<div class="header-copy">',
            '<p class="eyebrow">APPAM</p>',
            '<h1 data-i18n-en="Visualization Report" data-i18n-zh="可视化报告">Visualization Report</h1>',
            "</div>",
            '<div class="language-toggle" role="group" aria-label="Language">',
            '<button class="lang-button active" type="button" data-lang-switch="en" aria-pressed="true">EN</button>',
            '<button class="lang-button" type="button" data-lang-switch="zh" aria-pressed="false">中文</button>',
            "</div>",
            "</header>",
            '<div class="layout">',
            '<nav class="sidebar" aria-label="Report navigation">',
            '<h2 data-i18n-en="Samples" data-i18n-zh="样本">Samples</h2>',
            '<a class="nav-sample-link" href="#overview" data-i18n-en="Run overview" data-i18n-zh="运行概览">Run overview</a>',
            *nav_sections,
            "</nav>",
            "<main>",
            _overview_html(summary, settings, alpha_rows),
            *sections,
            "</main>",
            "</div>",
            '<div class="modal" id="image-modal" role="dialog" aria-modal="true" aria-hidden="true">',
            '<button class="modal-close" id="modal-close" type="button" data-i18n-en="Close" data-i18n-zh="关闭">Close</button>',
            '<div class="modal-content">',
            '<p class="modal-title" id="modal-title"></p>',
            '<img id="modal-image" alt="">',
            "</div>",
            "</div>",
            "<script>",
            'const modal = document.getElementById("image-modal");',
            'const modalImage = document.getElementById("modal-image");',
            'const modalTitle = document.getElementById("modal-title");',
            'const closeModalButton = document.getElementById("modal-close");',
            "const languageConfig = {",
            '  en: {htmlLang: "en", title: "APPAM Visualization Report", openPrefix: "Open "},',
            '  zh: {htmlLang: "zh-CN", title: "APPAM 可视化报告", openPrefix: "打开 "}',
            "};",
            "function translatedValue(element, lang, prefix){",
            "  return element.dataset[`${prefix}${lang === 'zh' ? 'Zh' : 'En'}`] || element.textContent;",
            "}",
            "function setLanguage(lang){",
            "  lang = languageConfig[lang] ? lang : 'en';",
            "  const config = languageConfig[lang];",
            "  document.documentElement.lang = config.htmlLang;",
            "  document.title = config.title;",
            '  document.querySelectorAll("[data-i18n-en]").forEach((element) => {',
            "    element.textContent = translatedValue(element, lang, 'i18n');",
            "  });",
            '  document.querySelectorAll(".zoomable").forEach((image) => {',
            "    const title = translatedValue(image, lang, 'title');",
            "    image.alt = title;",
            "    image.dataset.title = title;",
            '    const button = image.closest(".image-button");',
            "    if (button) button.setAttribute('aria-label', `${config.openPrefix}${title}`);",
            "  });",
            '  document.querySelectorAll("[data-lang-switch]").forEach((button) => {',
            "    const active = button.dataset.langSwitch === lang;",
            "    button.classList.toggle('active', active);",
            "    button.setAttribute('aria-pressed', active ? 'true' : 'false');",
            "  });",
            "  if (modal.classList.contains('open')) {",
            "    modalTitle.textContent = modalImage.alt;",
            "  }",
            "  try { localStorage.setItem('appam-report-language', lang); } catch (error) {}",
            "}",
            "function closeModal(){",
            '  modal.classList.remove("open");',
            '  modal.setAttribute("aria-hidden", "true");',
            '  modalImage.removeAttribute("src");',
            "}",
            'document.querySelectorAll(".zoomable").forEach((image) => {',
            '  image.addEventListener("click", () => {',
            "    modalImage.src = image.src;",
            "    modalImage.alt = image.alt;",
            "    modalTitle.textContent = image.dataset.title || image.alt;",
            '    modal.classList.add("open");',
            '    modal.setAttribute("aria-hidden", "false");',
            "  });",
            "});",
            'document.querySelectorAll("[data-lang-switch]").forEach((button) => {',
            "  button.addEventListener('click', () => setLanguage(button.dataset.langSwitch));",
            "});",
            'closeModalButton.addEventListener("click", closeModal);',
            'modal.addEventListener("click", (event) => {',
            "  if (event.target === modal) closeModal();",
            "});",
            'document.addEventListener("keydown", (event) => {',
            '  if (event.key === "Escape") closeModal();',
            "});",
            "let initialLanguage = 'en';",
            "try { initialLanguage = localStorage.getItem('appam-report-language') || 'en'; } catch (error) {}",
            "setLanguage(initialLanguage);",
            "</script>",
            "</body>",
            "</html>",
            "",
        ]
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a standalone HTML report from APPAM visualization outputs."
    )
    parser.add_argument("--visualization-dir", required=True, help="Visualization output directory.")
    parser.add_argument("--output", required=True, help="Output HTML report path.")
    parser.add_argument("--sample", action="append", required=True, help="Sample ID. Can be repeated.")
    parser.add_argument(
        "--embed-images",
        action="store_true",
        help="Embed image bytes as base64 data URIs instead of linking image files.",
    )
    return parser.parse_args(argv)


def run(args):
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        build_report_html(args.visualization_dir, args.sample, output, args.embed_images),
        encoding="utf-8",
    )


def main_from_snakemake(smk):
    output_html = Path(smk.output.html)
    output_data = Path(smk.output.data)
    log_path = Path(smk.log[0])
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_data.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    rows = read_summary_rows(smk.input.summary)
    alpha_rows = read_alpha_rows(
        path for path in smk.input.figures if str(path).endswith("alpha_diversity.tsv")
    )
    settings = report_settings(smk.config)
    samples = [str(sample) for sample in smk.params.samples]
    figure_keys = [str(key) for key in smk.params.figure_keys]
    summary = summarize_mag_rows(rows)
    payload = {
        "schema_version": 1,
        "samples": samples,
        "figures": figure_keys,
        "summary": summary,
        "alpha_diversity": alpha_rows,
        "settings": settings,
        "mag_summary": relpath(smk.input.summary, output_data),
    }
    output_data.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    output_html.write_text(
        build_report_html(
            smk.params.visualization_dir,
            samples,
            output_html,
            embed_images=True,
            enabled_figure_keys=figure_keys,
            summary_rows=rows,
            settings=settings,
            alpha_rows=alpha_rows,
        ),
        encoding="utf-8",
    )
    log_path.write_text(
        f"samples={len(samples)}\nfigures={len(figure_keys)}\n"
        f"mag_rows={len(rows)}\nalpha_rows={len(alpha_rows)}\n",
        encoding="utf-8",
    )


def main(argv=None):
    run(parse_args(argv))


if "snakemake" in globals():
    main_from_snakemake(snakemake)
elif __name__ == "__main__":
    main()
