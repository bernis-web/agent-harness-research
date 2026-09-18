"""CLI 入口(离线;真实执行入口默认拒绝)。"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from harness.contracts import RunConfig  # noqa: E402
from harness.providers import FakeModel  # noqa: E402
from harness.runner import Runner  # noqa: E402
from harness import scenarios, tasks  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["PA", "PB"], default="PA")
    ap.add_argument("--condition", choices=["C00", "C10", "C01", "C11"], default="C11")
    ap.add_argument("--scenario", default="defect_fix")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--runs-root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs"))
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--fault", default=None,
                    help="注入点: before_effect|after_effect_before_applied|"
                         "after_applied_before_checkpoint|score_persisted_before_log[:kind:stage]")
    args = ap.parse_args(argv)

    spec = tasks.build_pa() if args.task == "PA" else tasks.build_pb()
    script = (scenarios.pa_script(args.scenario) if args.task == "PA"
              else scenarios.pb_script())
    if args.fault:
        os.environ["HARNESS_FAULT"] = args.fault
    config = RunConfig(run_id=args.run_id, task_version=spec.task_version,
                       condition=args.condition, model_id="fake",
                       usage_metering="synthetic")
    runner = Runner(spec, config, args.runs_root, script, task=args.task)
    runner.run(resume=args.resume)
    print(f"run {args.run_id} finished; events at {runner.run_dir}/events.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
