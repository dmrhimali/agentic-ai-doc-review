"""Generate sample research-paper abstracts for relevance-review testing.

Simulates a systematic-review screening task: given the research question
"What are effective psychological interventions for PTSD in adults?",
classify each abstract as relevant (intervention study for adult PTSD) or
not relevant (unrelated topic, different population, non-intervention work).

Usage:
    python scripts/generate_test_docs.py [output_dir]

Creates 10 research-paper style documents (5 relevant + 5 not relevant)
with titles + structured abstracts — matching the format produced by
scripts/download_synergy_docs.py, so both test sets are interchangeable.
"""

import sys
from pathlib import Path

DOCUMENTS = {
    "cbt_ptsd_rct.txt": """\
Title: Cognitive behavioral therapy for adults with PTSD: a randomized trial

Abstract:
Background: Post-traumatic stress disorder (PTSD) is a debilitating
condition affecting approximately 6% of adults over the lifetime.
Cognitive behavioral therapy (CBT) is widely recommended, but
effect sizes across trials vary considerably.

Methods: We conducted a multi-site randomized controlled trial with
248 adults meeting DSM-5 criteria for PTSD. Participants were
randomized to 12 weeks of trauma-focused CBT (n=124) or waitlist
control (n=124). The primary outcome was change in Clinician-
Administered PTSD Scale (CAPS-5) score at 12 weeks, with follow-up
at 6 and 12 months.

Results: CBT produced a significantly larger reduction in CAPS-5
scores than waitlist control (mean difference -18.2 points, 95% CI
-22.1 to -14.3, p<0.001, Cohen's d=1.14). At 12-month follow-up,
64% of CBT participants no longer met criteria for PTSD versus 23%
of controls.

Conclusions: Trauma-focused CBT produces large and durable reductions
in PTSD symptoms in adults. Findings support current clinical
guidelines recommending CBT as first-line psychological treatment.
""",
    "emdr_veterans_study.txt": """\
Title: EMDR therapy in combat veterans with chronic PTSD: a pragmatic trial

Abstract:
Background: Many combat veterans with PTSD do not respond adequately
to standard CBT. Eye movement desensitization and reprocessing (EMDR)
is an alternative evidence-based therapy, but effectiveness data in
veteran populations remain limited.

Methods: Pragmatic trial at four Veterans Affairs medical centers.
Veterans (N=183) with chronic combat-related PTSD were randomized
to 12 sessions of EMDR or to present-centered therapy (active control).
Primary outcome was PCL-5 score at post-treatment. Secondary
outcomes included depression (PHQ-9) and functional impairment
(WHODAS 2.0).

Results: EMDR produced greater reductions in PCL-5 scores than
present-centered therapy (mean difference -9.4 points, 95% CI
-13.1 to -5.7). Clinically meaningful improvement (>10 point
PCL-5 reduction) was achieved by 58% in the EMDR arm versus 34%
in the control arm. Dropout rates were comparable across groups.

Conclusions: EMDR is an effective psychological intervention for
combat-related PTSD in veterans and should be offered as a
first-line option alongside trauma-focused CBT.
""",
    "prolonged_exposure_meta.txt": """\
Title: Prolonged exposure therapy for adult PTSD: a meta-analysis of trials

Abstract:
Background: Prolonged exposure (PE) therapy is a trauma-focused
treatment that has been tested in numerous randomized trials over
two decades. We synthesized the evidence to estimate pooled effects
and identify moderators of response.

Methods: We searched MEDLINE, Embase, PsycINFO, and CENTRAL through
December 2023 for randomized trials comparing PE to control
conditions in adults with PTSD. Two reviewers independently
extracted data and assessed risk of bias. Random-effects meta-
analysis estimated standardized mean differences (SMD).

Results: Thirty-one trials (N=3,847) met inclusion criteria. PE
produced large reductions in PTSD symptoms versus waitlist
(SMD=-1.22, 95% CI -1.48 to -0.96) and moderate reductions versus
active controls (SMD=-0.41, 95% CI -0.58 to -0.24). Effects were
consistent across trauma types and did not differ by session
number beyond 8 sessions.

Conclusions: Prolonged exposure therapy produces robust reductions
in PTSD symptoms. Evidence supports its designation as a first-line
psychological treatment in clinical practice guidelines.
""",
    "tf_cbt_refugees.txt": """\
Title: Trauma-focused CBT for refugees with PTSD: a multi-center trial

Abstract:
Background: Refugees experience PTSD at rates 10 times higher than
the general population, yet culturally adapted interventions are
understudied. We tested a trauma-focused CBT protocol adapted for
refugee populations.

Methods: Randomized trial across five European resettlement clinics.
Adult refugees (N=156) with PTSD were randomized to 16 sessions of
adapted trauma-focused CBT delivered with professional interpreters,
or to treatment-as-usual. Primary outcome was the Harvard Trauma
Questionnaire (HTQ) at 6 months.

Results: Adapted CBT produced greater HTQ reductions than usual care
(mean difference -0.72, 95% CI -0.91 to -0.53, p<0.001). Remission
rates were 47% versus 18%. Treatment gains were maintained at
12-month follow-up. Benefits held across trauma types and countries
of origin.

Conclusions: Culturally adapted trauma-focused CBT is effective for
refugees with PTSD. Routine implementation in resettlement services
could substantially reduce the mental-health burden in this population.
""",
    "group_cpt_sexual_assault.txt": """\
Title: Group cognitive processing therapy for PTSD in women: a trial

Abstract:
Background: Cognitive processing therapy (CPT) is effective for
PTSD but is typically delivered individually, limiting reach. We
evaluated whether group-delivered CPT produces comparable outcomes
in women with sexual-assault-related PTSD.

Methods: Single-blind randomized trial. Women (N=112) meeting
criteria for PTSD following sexual assault were randomized to
12 weekly sessions of group CPT (groups of 6-8) or individual CPT.
Primary outcome was CAPS-5 score at post-treatment, with a
non-inferiority margin of 5 points.

Results: Group CPT was non-inferior to individual CPT on the CAPS-5
(mean difference 2.1 points, 95% CI -1.3 to 5.4). Both modalities
produced large within-group reductions (d=1.34 and d=1.41). Group
participants reported higher satisfaction and perceived peer support.

Conclusions: Group-delivered CPT is non-inferior to individual CPT
for women with sexual-assault-related PTSD and offers greater
scalability. Findings support group delivery as a viable first-line
option.
""",
    "type2_diabetes_metformin.txt": """\
Title: Metformin vs sulfonylurea in type 2 diabetes: a cohort study

Abstract:
Background: Metformin is the recommended first-line agent for type
2 diabetes, but sulfonylureas remain widely prescribed. Real-world
comparative effectiveness data are limited.

Methods: Retrospective cohort study using electronic health records
from 412 primary care practices. Adults newly diagnosed with type 2
diabetes and started on either metformin or a sulfonylurea
(N=18,204) were followed for up to 5 years. Primary outcome was
time to a composite of myocardial infarction, stroke, or
cardiovascular death, adjusted using propensity-score weighting.

Results: Metformin was associated with a 22% lower hazard of the
composite endpoint (HR 0.78, 95% CI 0.68-0.89). Hypoglycemia
requiring medical attention was markedly less frequent on metformin
(1.1% vs 4.3% per year). HbA1c control was similar.

Conclusions: Metformin confers cardiovascular and safety advantages
over sulfonylureas as first-line therapy for type 2 diabetes,
supporting current guideline recommendations.
""",
    "childhood_asthma_inhaler.txt": """\
Title: Inhaled corticosteroid adherence in pediatric asthma: a cluster trial

Abstract:
Background: Poor adherence to inhaled corticosteroids drives avoidable
asthma exacerbations in children. We tested an electronic monitoring
and text-message feedback intervention in primary care.

Methods: Cluster-randomized trial across 48 pediatric primary care
practices. Children aged 6-14 with persistent asthma (N=1,108)
received either smart-inhaler monitoring plus weekly tailored
text-message feedback to caregivers, or usual care. Primary outcome
was adherence rate over 12 months.

Results: Mean adherence was 74% in the intervention arm versus 51%
in usual care (difference 23 percentage points, 95% CI 18-28).
Exacerbations requiring oral corticosteroids were reduced by 31%
(incidence rate ratio 0.69, 95% CI 0.56-0.85).

Conclusions: Smart-inhaler monitoring with tailored caregiver
feedback substantially improves adherence and reduces exacerbations
in pediatric asthma. Scalable implementation in primary care is
warranted.
""",
    "survey_methodology_nonresponse.txt": """\
Title: Nonresponse bias in population health surveys: a simulation study

Abstract:
Background: Declining response rates in health surveys threaten the
validity of population estimates. Various weighting and imputation
methods are used to adjust for nonresponse, but their relative
performance under realistic scenarios is unclear.

Methods: We conducted a Monte Carlo simulation study varying response
rates (20%-80%), nonresponse mechanisms (MCAR, MAR, MNAR), and sample
sizes (1,000-20,000). We compared raking, propensity weighting,
multiple imputation, and doubly robust estimators on bias and
coverage for prevalence estimates of a binary health outcome.

Results: Under MAR with strong auxiliary variables, all methods
produced approximately unbiased estimates. Under MNAR, all methods
exhibited substantial residual bias, though doubly robust estimators
showed slightly better coverage. Sample size affected variance but
not bias.

Conclusions: No adjustment method fully recovers unbiased estimates
under nonresponse-not-at-random. Survey designs should prioritize
collecting rich auxiliary information and consider sensitivity
analyses for MNAR scenarios.
""",
    "supply_chain_logistics.txt": """\
Title: Predictive maintenance in cold-chain logistics: an RL approach

Abstract:
Background: Cold-chain logistics require strict temperature control,
and refrigeration failures generate costly spoilage. Traditional
preventive-maintenance schedules are inefficient under variable
operating conditions.

Methods: We developed a deep reinforcement learning agent (PPO-based)
to schedule maintenance across a fleet of 1,200 refrigerated
containers. The agent observed telemetry (vibration, temperature
variance, door events) and chose when to trigger inspections.
We evaluated against fixed-interval and condition-based baselines
over 18 months of historical data in simulation.

Results: The RL policy reduced spoilage incidents by 38% and total
maintenance cost by 21% versus fixed-interval scheduling. It
outperformed condition-based maintenance on both metrics,
particularly for long-haul routes with variable ambient conditions.

Conclusions: Reinforcement learning produces effective adaptive
maintenance policies for cold-chain logistics. Deployment trials
are underway at a major global logistics operator.
""",
    "editorial_mental_health_funding.txt": """\
Title: Rethinking mental health funding priorities: an editorial perspective

Abstract:
Mental health disorders account for a substantial share of the global
burden of disease, yet mental health receives only a small fraction
of health-care budgets in most countries. In this editorial, we
argue that current funding structures under-invest in prevention,
early intervention, and workforce development.

We review trends in mental health spending across OECD countries
over the past decade and highlight three persistent gaps: limited
community-based services, inadequate integration with primary care,
and insufficient research on implementation. We contrast the
biomedical framing that dominates funding decisions with a
population-health framing that would prioritize social determinants.

We call on policymakers, funders, and professional societies to
reallocate resources toward scalable community interventions and
toward implementation research capable of identifying which
interventions work in routine settings. Absent such reorientation,
the gap between evidence-based treatments and accessible care will
continue to widen.

This editorial does not present new empirical data; it synthesizes
existing policy literature to motivate a change in funding strategy.
""",
}


def generate(output_dir: str) -> None:
    """Write all sample documents to the output directory."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for filename, content in DOCUMENTS.items():
        (out / filename).write_text(content, encoding="utf-8")
        print(f"  + {filename}")

    print(f"\nDone. {len(DOCUMENTS)} documents written to {out}")


def main() -> None:
    """Generate test documents."""
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "./test-docs"
    print(f"Generating test documents in {output_dir}...")
    generate(output_dir)


if __name__ == "__main__":
    main()
