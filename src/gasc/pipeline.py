from __future__ import annotations

from pathlib import Path
from shutil import copytree

from concurrent.futures import ThreadPoolExecutor, as_completed

from gasc.clients.bedrock import bedrock_runtime
from gasc.config import AppConfig
from gasc.io import load_jsonl, write_jsonl
from gasc.judge import judge_label
from gasc.paths import repo_root
from gasc.schemas import FrozenPrompt, PromptVariant, Seed, VariantValidation
from gasc.seeds import make_seeds
from gasc.validation import validate_variant
from gasc.variants import make_variants

FIXTURE_SEEDS = repo_root() / "data" / "fixtures" / "fixture_seeds.jsonl"


def _stage_dir(cfg: AppConfig, name: str) -> Path:
    return cfg.out / name


def reuse_frozen_stages(cfg: AppConfig) -> None:
    if not cfg.reuse_from:
        return
    src = Path(cfg.reuse_from)
    for name in ("1_seeds", "2_validated_seeds", "3_variants", "4_validated_prompts"):
        dest = _stage_dir(cfg, name)
        if dest.exists():
            continue
        origin = src / name
        if origin.exists():
            copytree(origin, dest)


def stage_build_seeds(cfg: AppConfig) -> list[Seed]:
    out = _stage_dir(cfg, "1_seeds") / "seeds.jsonl"
    if out.exists():
        return load_jsonl(out, Seed)[: cfg.seed_limit]
    if not cfg.use_fixture_seeds:
        seeds = make_seeds(cfg.seed_limit)
        write_jsonl(out, seeds)
        return seeds
    seeds = load_jsonl(FIXTURE_SEEDS, Seed)[: cfg.seed_limit]
    write_jsonl(out, seeds)
    return seeds


def stage_validate_seeds(cfg: AppConfig, seeds: list[Seed]) -> list[Seed]:
    out = _stage_dir(cfg, "2_validated_seeds") / "validated_seeds.jsonl"
    if out.exists():
        return load_jsonl(out, Seed)
    kept = [s for s in seeds if s.intent.strip()]
    write_jsonl(out, kept)
    return kept


def stage_generate_variants(cfg: AppConfig, seeds: list[Seed]) -> list[PromptVariant]:
    out = _stage_dir(cfg, "3_variants") / "variants.jsonl"
    if out.exists():
        return load_jsonl(out, PromptVariant)
    rows: list[PromptVariant] = []
    allowed = set(cfg.variants)
    for seed in seeds:
        for variant in make_variants(seed):
            if variant.variant in allowed:
                rows.append(variant)
    write_jsonl(out, rows)
    return rows


def stage_validate_variants(cfg: AppConfig, variants: list[PromptVariant], seeds: list[Seed]) -> list[FrozenPrompt]:
    out = _stage_dir(cfg, "4_validated_prompts") / "prompts.jsonl"
    val_path = _stage_dir(cfg, "4_validated_prompts") / "all_validations.jsonl"
    if out.exists():
        return load_jsonl(out, FrozenPrompt)
    seed_ids = {s.seed_id for s in seeds}
    labels: dict[str, str | None] = {v.variant_id: None for v in variants}
    if not cfg.skip_llm:
        import os

        from dotenv import load_dotenv

        load_dotenv(repo_root() / ".env")
        model_id = os.environ.get("GASC_JUDGE_MODEL") or cfg.models.judge
        client = bedrock_runtime(os.environ.get("AWS_REGION", "us-east-1"))
        workers = max(1, int(os.environ.get("GASC_JUDGE_WORKERS", "6")))

        def _one(variant: PromptVariant) -> tuple[str, str | None]:
            return variant.variant_id, judge_label(client, model_id=model_id, variant=variant)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_one, v) for v in variants]
            for i, fut in enumerate(as_completed(futs), start=1):
                vid, lab = fut.result()
                labels[vid] = lab
                if i % 50 == 0 or i == len(variants):
                    print(f"judge {i}/{len(variants)}", flush=True)
    validations: list[VariantValidation] = []
    accepted_by_seed: dict[str, list[FrozenPrompt]] = {}
    for variant in variants:
        # G_light / ApplyGuardrail / Maverick are never consulted for accepted.
        check = validate_variant(
            variant,
            seed_ids=seed_ids,
            judge_label=labels.get(variant.variant_id),  # type: ignore[arg-type]
            skip_llm=cfg.skip_llm,
            g_light_q=None,
            apply_guardrail_action=None,
        )
        validations.append(check)
        if check.accepted:
            accepted_by_seed.setdefault(variant.seed_id, []).append(
                FrozenPrompt(**variant.model_dump(), accepted=True)
            )
    frozen: list[FrozenPrompt] = []
    for seed_id in sorted(seed_ids):
        family = accepted_by_seed.get(seed_id) or []
        if len(family) == 4:
            frozen.extend(family)
    write_jsonl(val_path, validations)
    write_jsonl(out, frozen)
    return frozen


def run_pipeline(cfg: AppConfig) -> list[FrozenPrompt]:
    reuse_frozen_stages(cfg)
    seeds = stage_build_seeds(cfg)
    seeds = stage_validate_seeds(cfg, seeds)
    variants = stage_generate_variants(cfg, seeds)
    return stage_validate_variants(cfg, variants, seeds)
