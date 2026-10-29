"""Publish already analyzed diagnostic evidence; no physics execution."""
from pathlib import Path
import json
import hashlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"]="kamino-pd-convergence-2026-10-29"
import matplotlib.pyplot as plt
from analyze import ROOT,HERE,read,save,sha,rel,load_active


TITLES={"budget1000":"有界 PD：200 与 1000 次迭代预算","compl1e6":"有界 PD：仅改变互补停止容差","noaccel":"有界 PD：仅关闭加速","noprecondition":"有界 PD：仅关闭对角预条件"}
NAMES={"budget1000":"config.padmm.max_iterations","compl1e6":"config.padmm.compl_tolerance","noaccel":"config.padmm.use_acceleration","noprecondition":"config.dynamics.preconditioning"}


def observation(v,a,b):
    if v=="budget1000":
        return f"200→1000 次迭代后，原严格三容差 1e-7 下收敛比例仍为 0%；终止残差及 body/joint 轨迹逐元素相同，r_c 中位数 {a['terminal_rc_median_J']:.6g} J。预定六个时间步的尾20次有界行 x/y/z 均不再变化，支持持续停滞而非仅200次预算不足。"
    if v=="compl1e6":
        return f"仅将互补容差从 1e-7 改为 1e-6 J，配置收敛比例由 0% 到 100%，最多 {b['iterations_max']} 次；按原严格三容差重算仍为 0%。r_c 中位数仍为 {b['terminal_rc_median_J']:.6g} J。这识别了停止门槛，不是严格收敛问题已经解决。"
    if v=="noaccel":
        return f"仅关闭加速，严格收敛比例仍为 0%，用满200次；r_c 中位数 {b['terminal_rc_median_J']:.6g} J，最大值 {b['terminal_rc_max_J']:.6g} J。该对照未消除停滞，不能把失败归结为仅加速分支。"
    return f"仅关闭对角预条件，严格收敛比例仍为 0%，r_c 中位数从 {a['terminal_rc_median_J']:.6g} 升至 {b['terminal_rc_median_J']:.6g} J；200次下数值残差更大。物理力矩/轨迹仍通过事前门槛，不能据此推荐关闭预条件或声称收敛修复。"


def main():
    a=read(HERE/"analysis.json");p=read(HERE/"protocol.json")
    if a["status"]!="passed":raise ValueError("Cannot publish invalid evidence")
    params=read(ROOT/"solvers/kamino/parameters.json")["records"]
    ids={x["name"]:x["id"] for x in params}
    runs={(r["variant"],r["repeat"]):r for r in a["runs"]}
    cases=[]
    for spec in p["pair_cases"]:
        v=spec["B"];cid=spec["id"];variants=[];replay=[];data={};iters={}
        for letter,name in (("A","baseline"),("B",v)):
            r=runs[(name,1)];r2=runs[(name,2)];path=ROOT/r["run"];config=read(path/"resolved-config.json");env=read(path/"environment.json")
            with np.load(path/"trajectory.npz") as z:data[letter]={k:z[k].copy() for k in z.files}
            iters[letter]=load_active(path/"iterations.npz")
            variants.append({"variant":letter,"label":name,"run_id":r["run_id"],"metrics":r["metrics"],"raw_file":r["raw_file"],"raw_sha256":r["raw_sha256"],"program_sha256":r["program_sha256"],"protocol_sha256":r["protocol_sha256"],"iteration_file":r["iteration_file"],"iteration_sha256":r["iteration_sha256"],"config":{"treatment":p["variants"][name],"resolved":{"padmm":config["solver"]["padmm"],"dynamics":config["solver"]["dynamics"]},"full_config_file":rel(path/"resolved-config.json")},"environment":{k:env[k] for k in ("python","platform","packages","device","source_commit")},"result_file":rel(path/"result.json"),"reproduction":{"run_id":r2["run_id"],"raw_file":r2["raw_file"],"raw_sha256":r2["raw_sha256"],"program_sha256":r2["program_sha256"],"protocol_sha256":r2["protocol_sha256"],"iteration_file":r2["iteration_file"],"iteration_sha256":r2["iteration_sha256"],"result_file":r2["run"]+"/result.json"}})
            replay.append({"variant":letter,"label":name,"times":data[letter]["t"].tolist(),"body_q":data[letter]["body_q"].tolist(),"body_names":["rotor"],"sample_kind":"time"})
        fig,ax=plt.subplots(1,3,figsize=(13,3.5),constrained_layout=True)
        for letter in ("A","B"):
            label="baseline" if letter=="A" else v
            z=data[letter];it=iters[letter];m=it["outer_step"]==0
            ax[0].semilogy(z["t"][1:],z["status_r_c"][1:,0],label=label)
            ax[1].semilogy(it["status_iterations"][m,0],np.maximum(it["status_r_c"][m,0],1e-16),label=label)
            ax[2].plot(z["t"],z["joint_q"][:,0],label=label)
        for k in (0,1):ax[k].axhline(1e-7,color="black",linestyle="--",linewidth=.9,label="strict 1e-7 J")
        for k,x,y in ((0,"time [s]","terminal r_c [J]"),(1,"iteration, physical step 0","r_c [J]"),(2,"time [s]","joint angle [rad]")):
            ax[k].set_xlabel(x);ax[k].set_ylabel(y);ax[k].legend(fontsize=7);ax[k].grid(alpha=.25)
        fig.suptitle(cid+" | physical acceptance does not imply strict convergence",fontsize=10)
        fig.savefig(HERE/(cid+".svg"),metadata={"Date":None});fig.savefig(HERE/(cid+".png"),dpi=130);plt.close(fig)
        acceptance={"analysis_file":rel(HERE/"analysis.json"),"analysis_sha256":sha(HERE/"analysis.json"),"runs":[{"run_id":runs[(name,n)]["run_id"],"evidence_passed":runs[(name,n)]["status"]=="passed","physical_criteria":runs[(name,n)]["physical_criteria"],"configured_converged_fraction":runs[(name,n)]["metrics"]["configured_converged_fraction"],"strict_converged_fraction":runs[(name,n)]["metrics"]["strict_converged_fraction"]} for name in ("baseline",v) for n in (1,2)],"comparison":next(c for c in a["comparisons"] if c["id"]==cid),"repeat_checks":[c for c in a["checks"] if any((" "+name+"/") in c["name"] for name in ("baseline",v))],"configuration_check":next(c for c in a["checks"] if c["name"]=="exact single-factor diff "+v)}
        cases.append({"id":cid,"title":TITLES[v],"solver":"kamino","experiment_kind":"mechanism","observation":observation(v,variants[0]["metrics"],variants[1]["metrics"]),"physical_acceptance":"passed","strict_convergence_acceptance":"failed_criteria","limitations":"仅固定的CPU单转子饱和场景，物理门槛通过不代表严格收敛通过；未证明普适float32精度下限，没有改求解器实现；每迭代观测同步开销不支持性能排名。","association_scope":"相同物理初态和驱动，直接单因素比较 "+NAMES[v]+"；严格 baseline 在四个配对页复用，两次独立重复按唯一run计数。","association_relation":"measures_behavior_of","associations":[ids[NAMES[v]]],"source_refs":p["source_refs"],"variants":variants,"protocol_file":runs[("baseline",1)]["run"]+"/protocol.json","runner_file":runs[("baseline",1)]["run"]+"/runner.py","plot":"convergence/"+cid+".svg","curve_file":rel(HERE/(cid+".svg")),"replay":replay,"sample_kind":"time","acceptance_results":acceptance})
    evidence={rel(f):sha(f) for f in HERE.rglob("*") if f.is_file() and f.name!="publication.json" and "__pycache__" not in str(f)}
    for case in cases:
        case["observation"]="两设置均通过冻结的物理门槛；"+case["observation"]
    summary={"physical_passed_runs":10,"original_strict_convergence_resolved":False,"baseline_representative_steps":runs[("baseline",1)]["diagnostics"],"budget1000_representative_steps":runs[("budget1000",1)]["diagnostics"],"interpretation":"baseline与1000的预定六步尾20次有界x/y/z不变；第0步x距上界26ULP，gap约9.68575e-8乘|z|4.39956生成rc4.26130e-7J，非零对偶增量小于z半ULP2.38419e-7并在float32加法中丢失。支持当前算术与缩放下量化停滞，未证明普适floor；仅放宽互补容差不算严格收敛修复。"}
    save(HERE/"publication.json",{"status":"passed","formal_runs":10,"cases":cases,"summary":summary,"evidence_files":evidence,"analysis_file":rel(HERE/"analysis.json"),"analysis_sha256":sha(HERE/"analysis.json"),"publisher_sha256":sha(__file__),"scope":"Physical pass and evidence pass are separate from the unresolved original strict convergence failure."})
    print(json.dumps({"status":"passed","cases":4,"formal_runs":10,"evidence_files":len(evidence)}))


if __name__=="__main__":main()
