# AI-Based-Cloud-Backup-Optimization-System-for-Smart-Hospitals
Predictive, cost-aware EHR backup scheduling for hospitals — LSTM demand forecasting + criticality-based prioritization on AWS.


**Course:** BCSE355L – Cloud Architecture Design

**Team:**
- Shrish V P — 24BIT0072
- Gokul S — 24BIT0147
- Joy Kevin L M — 24BIT0098

---

## 1. Abstract

Smart hospitals generate rapidly growing volumes of Electronic Health Record (EHR) data — imaging files, clinical notes, monitoring logs, and transactional records — that must be backed up reliably to survive hardware failure, ransomware, or natural disaster. Existing cloud backup and disaster recovery systems, however, are largely reactive: they replicate and restore data on fixed schedules or static thresholds without anticipating how much data will need to be backed up, when demand will spike, or which records are most critical to protect first.

A review of 15 recent papers (2023–2026) confirms this gap. Disaster-recovery architectures (active-active replication, hash-free mobile sync) prove reliable backup mechanics but include no intelligence. Predictive AI papers (LSTM auto-scaling, RL-based scheduling, autonomous self-healing cloud) demonstrate strong forecasting and automation but target generic cloud infrastructure, not hospital-specific EHR workloads. Healthcare-focused papers (federated diagnostics, HPE GreenLake disaster recovery) apply AI to clinical prediction or infrastructure but not to backup scheduling itself. No reviewed work combines predictive workload forecasting, healthcare-aware data prioritization, and AWS-native backup automation into one system.

This project proposes an AI-based cloud backup optimization system for smart hospitals that uses machine learning (LSTM/time-series models) to forecast EHR storage growth and backup demand, dynamically schedules backups based on predicted workload and record criticality, and tiers storage cost-efficiently using AWS services. The system uses **Amazon S3** for tiered storage, **AWS Lambda** for automated backup triggers, **Amazon SageMaker** for the predictive model, **AWS Backup/Step Functions** for orchestration, and **CloudWatch/QuickSight** for monitoring and visualization — delivering a backup pipeline that is predictive, cost-aware, and prioritizes critical medical data rather than treating all records equally.

---

## 2. Problem Statement

Hospitals store enormous and constantly growing volumes of patient data — EHRs, diagnostic images, monitoring streams, and administrative records — all of which must be backed up reliably to guarantee continuity of care. Current cloud backup systems typically operate on fixed schedules (e.g., nightly full backups, weekly incrementals) or simple threshold rules, regardless of actual data growth patterns or how critical a given dataset is.

This creates two concrete problems:

1. **Inefficient resource use** — storage is over-provisioned during quiet periods and under-provisioned during surges (e.g., after a mass casualty event or system-wide EHR migration), leading to either wasted cloud spend or missed/delayed backups.
2. **No prioritization** — existing systems treat all data equally; a routine administrative log and a critical patient record are backed up on the same schedule, with no mechanism to prioritize what matters most when time or bandwidth is constrained.

The papers reviewed confirm that solutions to date address only fragments of this problem: reliable backup mechanics without intelligence (Paper Set 1), general-purpose predictive cloud AI without healthcare context (Paper Set 2), and healthcare AI without backup-specific optimization (Paper Set 3). No existing system predicts hospital-specific backup demand, schedules backups intelligently based on that prediction, and prioritizes critical medical data — all on a cost-efficient AWS-native pipeline.

---

## 3. Proposed Solution

A predictive, AI-driven cloud backup optimization system purpose-built for smart hospitals, structured in three stages:

### Stage 1 — Predictive Workload Forecasting
An LSTM-based (or hybrid CNN-LSTM/BiLSTM) time-series model is trained on historical EHR access and storage-growth patterns to forecast near-term backup demand — how much new/changed data will need backing up, and when load is likely to spike (e.g., admission surges, imaging-heavy periods).

### Stage 2 — Intelligent, Priority-Aware Backup Scheduling
Rather than fixed full/incremental schedules, the system dynamically decides when to back up and what to back up first. Records are tagged by criticality (e.g., active-patient EHRs and imaging vs. archival administrative logs), so critical data is prioritized during constrained backup windows, and backup frequency adjusts automatically to predicted load rather than a static calendar.

### Stage 3 — Cost-Aware, Automated Cloud Execution
Backups execute through an AWS-native pipeline: Lambda functions trigger backup jobs based on the model's predictions, data is tiered across S3 storage classes (Standard → Infrequent Access → Glacier) based on predicted access frequency and criticality, and Step Functions orchestrate the full backup/recovery workflow. CloudWatch monitors system health and SNS alerts staff to backup failures or anomalies, while QuickSight visualizes storage growth trends, backup success rates, and cost savings.

Together, this closes the gap identified across all 15 papers: predictive intelligence, healthcare-aware prioritization, and AWS-native backup automation combined in a single working system — rather than as three separate research threads.

---

## 4. Literature Survey

A total of 15 research papers (2023–2026) were reviewed and divided evenly among the three team members, five papers each.

| # | Paper Title (Year) | Method / Dataset | Advantages / Limitations | Research Gap |
|---|---|---|---|---|
| 1 | Design and Construction of Data Center Disaster Recovery Backup System Based on Cloud Storage (2024) | **Method:** Active-active DR architecture using global load balancing, storage/database replication, Oracle RAC clustering, virtualization, network failover.<br>**Dataset:** Simulation-based cloud data center environment; DR experiments on full, incremental, and differential backups | **Adv:** High availability and fault tolerance; validated backup/recovery efficiency; strong active-active architecture.<br>**Lim:** No AI or predictive analytics; no intelligent scheduling; not healthcare-specific | Lacks predictive ML for forecasting backup demand, storage growth, or system failures for smart hospitals |
| 2 | Data Science Approaches to Cloud Security Optimization (2025) | **Method:** Ensemble trees, deep learning, clustering, vector regression, feature selection, predictive analytics.<br>**Dataset:** 12 cloud storage systems, 23 security measures, 3,500 synthetic predictive outcomes across AWS S3, Azure, GCP, Dropbox, OneDrive, Box, pCloud | **Adv:** High prediction accuracy (up to 96%); identifies optimal security configurations; proactive threat detection.<br>**Lim:** Focuses on security, not backup optimization; uses synthetic datasets; not healthcare-specific | Predicts cloud security performance but not backup strategies or healthcare data growth |
| 3 | Cloud-Powered Federated Learning for Global Healthcare Diagnostics (2025) | **Method:** Multi-Cloud Federated Learning (MC-FL): adaptive/secure aggregation, differential privacy, gradient compression.<br>**Dataset:** NIH ChestX-ray14 and MIMIC-III across simulated healthcare institutions on AWS, Azure, GCP | **Adv:** 98.21% diagnostic accuracy; >50% lower communication cost; privacy-preserving, multi-cloud fault tolerance.<br>**Lim:** Focuses on diagnostics, not backup optimization; no storage-tier management; simulated environment only | Enables secure federated healthcare AI but does not address intelligent backup management |
| 4 | Efficient Hash-Free Mobile Cloud Backup via Operation-Log Versioning (2026) | **Method:** SolFS file-system architecture: operation-log versioning, hash-free delta synchronization, shadow-file optimization.<br>**Dataset:** Real mobile workloads on Google Pixel 8, Android 14, Ubuntu server, Dropbox, Facebook, Twitter, CapCut | **Adv:** Eliminates hash computation; reduces sync latency, CPU, energy, network overhead.<br>**Lim:** No AI or predictive analytics; mobile-focused only; not healthcare-specific | Improves backup efficiency mechanically but lacks intelligent prediction of backup workload/demand |
| 5 | Knowledge-Based Dynamic Early Warning for Environmental Risks in Pumped Storage Projects (2026) | **Method:** Knowledge graph construction using BERT-IE, Graph-BERT, KG-STGAT, adaptive thresholds, intelligent decision-making.<br>**Dataset:** 3 years monitoring data (10,800 samples), 12 environmental indicators, 200 historical risk cases, 10 industry standards | **Adv:** High prediction accuracy (94.7%); real-time early warning; knowledge-driven reasoning.<br>**Lim:** Domain-specific to environmental risk; no cloud backup optimization; no healthcare implementation | Effective AI prediction/decision-making but limited to environmental risk, not healthcare backup |
| 6 | Cloud-edge Collaborative Resource Optimization for Distributed Storage in CDNs (2026) | **Method:** MDS erasure coding, adaptive redundancy allocation, greedy algorithm, backtracking with pruning.<br>**Dataset:** Simulation-based CDN and distributed cloud storage scenarios with varying popularity, cost, reliability | **Adv:** Optimizes storage allocation and redundancy jointly; outperforms traditional replication schemes.<br>**Lim:** Does not use AI/ML; CDN-focused, not healthcare; no intelligent backup scheduling | Static optimization only — lacks AI-driven prediction of storage growth or backup demand |
| 7 | Hybrid Cloud IT Infrastructure Maintenance Using AI (2025) | **Method:** AI-assisted hybrid cloud maintenance: automated backup management, predictive maintenance, anomaly detection, intelligent scheduling.<br>**Dataset:** Hybrid cloud infrastructure data — VMs, servers, logs, backup metadata, utilization metrics from enterprise environments | **Adv:** Automates maintenance and backup scheduling; predicts hardware/storage failures proactively.<br>**Lim:** No novel ML model or benchmarking; not healthcare-specific; lacks long-term growth forecasting | AI-assisted framework exists but lacks EHR-specific forecasting and AWS-native backup optimization |
| 8 | Autonomous Cloud Management Using AI: Self-Healing and Self-Optimization (2023) | **Method:** AI-driven autonomous cloud management: K-means/PCA anomaly detection, LSTM/RNN prediction, RL (Q-Learning, DQN) recovery, GA/PSO load balancing.<br>**Dataset:** Simulated cloud environment (Apache CloudStack, OpenStack) with synthetic workloads via JMeter, Prometheus, Grafana | **Adv:** Strong self-healing and auto-scaling via multiple AI techniques; reduces downtime and operational cost.<br>**Lim:** Evaluated only in simulation; generic cloud, not healthcare; no EHR-specific backup logic | Rich AI toolset for autonomous cloud ops, but not applied to hospital backup prioritization |
| 9 | Enhancing Cloud Storage Efficiency with AI: A Comprehensive Review (2024) | **Method:** Review of AI/ML techniques: LSTM storage optimization, DQN caching, AI-based tiering, deduplication, lifecycle management.<br>**Dataset:** Survey synthesizing multiple studies (100M cloud files, 50PB storage data, 1B access records, EHR datasets up to 100TB) | **Adv:** 30–45% storage cost reduction reported; broad technique coverage including EHR datasets.<br>**Lim:** Survey only, no implementation; no AWS-specific detail; no backup scheduling focus | Wide AI coverage reviewed, but not synthesized into a working predictive backup system |
| 10 | AI-Driven Optimization, Resource Management, and Security in Cloud Computing (2024) | **Method:** Review of ML/RL/fuzzy logic for workload forecasting, autoscaling, anomaly detection, fault tolerance.<br>**Dataset:** Survey synthesizing cloud infrastructure data, workload traces, logs, and cybersecurity events | **Adv:** Broad cross-domain AI coverage for cloud reliability and resource management.<br>**Lim:** Survey only; no backup-specific focus; healthcare barely discussed | General cloud AI reviewed extensively, but not translated into healthcare backup optimization |
| 11 | AI-Driven Predictive Auto-Scaling for Cloud-Native Systems with Real-Time Anomaly Detection (2024) | **Method:** LSTM-based predictive auto-scaling with unsupervised anomaly detection.<br>**Dataset:** Simulation-based AWS observability metrics, historical workload traces, resource utilization logs | **Adv:** Proactively predicts demand; outperforms reactive threshold-based scaling.<br>**Lim:** Not healthcare-specific; no backup scheduling or disaster recovery planning | Strong LSTM predictive framework not extended to EHR growth or backup scheduling |
| 12 | Robust Healthcare Systems Utilising HPE GreenLake for Disaster Recovery and ML Integration (2025) | **Method:** Hybrid cloud framework (HPE GreenLake) using XGBoost, LightGBM, Transformer models for clinical data + automated backup/recovery.<br>**Dataset:** Healthcare data from patient monitoring devices, cloud EHR systems, clinical records | **Adv:** Combines disaster recovery with ML-based clinical risk prediction; automatic backup and rapid recovery.<br>**Lim:** Vendor-specific (not AWS); no predictive backup-workload model; no storage-cost optimization | ML + DR combined for healthcare, but no AWS-native predictive backup scheduling |
| 13 | Performance Optimization Techniques for Cloud-Based EHR Storage Systems (2026) | **Method:** Review of performance optimization techniques: DenseBN deep learning, blockchain-IPFS hybrids, caching, compression.<br>**Dataset:** Survey of EHR datasets, cloud storage benchmarks, hybrid cloud simulations (2021–2025 publications) | **Adv:** Healthcare-specific storage optimization synthesis; covers performance-security-compliance trade-offs.<br>**Lim:** Review only, no experimental validation; no AWS backup services; no predictive analytics | Covers EHR storage performance deeply but not backup scheduling or growth forecasting |
| 14 | AI-Enhanced Queueing and Scheduling Systems in Cloud Computing (2025) | **Method:** Dual-layer neural network with reinforcement learning for dynamic task scheduling.<br>**Dataset:** Simulated cloud environment, synthetic workload traces benchmarked against FIFO/round-robin | **Adv:** 30% reduction in task waiting time; 91% peak resource utilization; 20–35% higher throughput.<br>**Lim:** Simulated only; not healthcare-specific; no HIPAA/compliance consideration | Strong RL scheduling approach, unapplied to hospital backup prioritization |
| 15 | Machine Learning-Based Cloud Resource Allocation Algorithms: A Comparative Review (2025) | **Method:** Comparative review of BiLSTM, Grid LSTM, CNN-LSTM hybrids, PSO-GA for workload prediction.<br>**Dataset:** Survey synthesizing CloudSim simulations, real-world traces from Google Cloud and Azure | **Adv:** >92% prediction accuracy across models; effectively handles nonstationary workload data.<br>**Lim:** Survey only; no healthcare application; no AWS-specific deployment | Identifies best-fit predictive models but doesn't apply them to EHR backup demand forecasting |

---

## 5. Individual Research Gap Analysis

**Shrish V P (24BIT0072, Papers 1–5):**
Existing disaster-recovery and backup-mechanics research (active-active replication, hash-free mobile sync) is mature and reliable but entirely non-intelligent — no forecasting, no prioritization. Adjacent AI work (cloud security prediction, federated healthcare diagnostics, knowledge-graph early warning) proves that predictive ML performs well in cloud and healthcare contexts individually, but none of it is aimed at backup demand or storage-growth forecasting. Assessment: the reliable backup infrastructure exists; what's missing is layering a predictive model (informed by the accuracy shown in the security-optimization and knowledge-graph papers) on top of it, specifically trained on EHR growth patterns.

**Gokul S (24BIT0147, Papers 6–10):**
The general cloud-AI literature is rich in individual techniques — erasure coding for storage efficiency, RL/GA-based self-healing, LSTM-based storage tiering — and reviews confirm these techniques already deliver measurable cost/performance gains (30–45% storage cost reduction, strong autoscaling results). However, every one of these five papers is either healthcare-agnostic or purely a survey with no working implementation. Assessment: the building blocks for an intelligent backup system are proven in generic cloud settings; the gap is domain adaptation — retraining/repurposing these forecasting and self-healing techniques specifically for EHR backup workloads and validating them with AWS-native services rather than generic simulated environments.

**Joy Kevin L M (24BIT0098, Papers 11–15):**
The healthcare-adjacent papers here (HPE GreenLake DR + ML, EHR storage performance review) show that ML and disaster recovery can be combined in clinical settings, and the generic AI papers (LSTM auto-scaling, RL scheduling, comparative ML reviews) show predictive models reliably outperform static/reactive approaches (e.g., 30% lower waiting time, >92% prediction accuracy). But none combine both: healthcare context + predictive scheduling + AWS-native execution. Assessment: the missing piece is specifically an AWS-integrated predictive scheduler that treats EHR criticality as a first-class scheduling input, which none of these five papers attempt.

**Combined Team Research Gap:**
Across all 15 papers, three separate research threads exist — (1) reliable cloud backup/DR mechanics, (2) generic predictive AI for cloud resource/workload management, and (3) healthcare-specific AI applications (diagnostics, clinical DR) — but no reviewed work merges all three into a predictive, priority-aware, AWS-native backup system for smart hospitals. This is the gap this project addresses.

---

## 6. Project Objectives

1. Develop an LSTM-based predictive model to forecast EHR storage growth and backup workload demand for a simulated smart-hospital environment.
2. Design and implement an intelligent backup scheduler that dynamically adjusts backup frequency and timing based on predicted demand, rather than fixed schedules.
3. Implement criticality-based data prioritization so that active-patient and diagnostic-critical records are backed up ahead of low-priority administrative data during constrained windows.
4. Integrate AWS-native services (S3 tiering, Lambda, SageMaker, Step Functions) to automate the full predict-schedule-execute backup pipeline.
5. Reduce cloud storage cost through predictive, tiered storage allocation compared to a static full/incremental backup baseline (target: measurable % reduction, benchmarked against Paper 9's reported 30–45%).
6. Visualize backup performance, predicted vs. actual demand, and cost savings through a monitoring dashboard (CloudWatch + QuickSight).

---

## 7. Novelty Summary

What makes this project different from existing work:

- **Predictive + priority-aware backup fusion:** No reviewed paper combines demand forecasting and medical-record criticality-based prioritization in one scheduling decision. Existing predictive-scheduling papers (Papers 11, 14) are healthcare-agnostic; existing healthcare-DR papers (Paper 12) have no predictive model.
- **Better algorithm:** Uses an LSTM/time-series forecasting approach (validated at >90% accuracy in Papers 11 and 15) specifically retrained on EHR access/growth patterns, rather than generic cloud workload traces.
- **Better architecture:** A three-stage pipeline (forecast → prioritized schedule → automated tiered execution) versus the single-stage approaches seen across all 15 papers (either backup mechanics or prediction, never both in sequence).
- **Better AWS integration:** Unlike Paper 12 (vendor-locked to HPE GreenLake) and Paper 13 (no AWS discussion at all), this project is built natively on AWS (S3, Lambda, SageMaker, Step Functions, CloudWatch), directly answering the "Future Work" call repeated across nearly all 15 papers to integrate predictive ML with AWS cloud services.
- **Better cost-efficiency:** Applies predictive S3 storage-class tiering (Standard/IA/Glacier) driven by forecasted access frequency, rather than static tiering rules — targeting the cost reductions reported in Paper 9 but applied specifically to backup, not general storage.
- **Better automation:** Fully automated trigger-to-execution pipeline (Lambda + Step Functions) instead of the manual/scheduled triggers implicit in Papers 1 and 4.
- **Better scalability:** Designed to scale with hospital data growth using cloud-native elastic storage, addressing the storage-growth blind spot flagged as a limitation in Papers 1, 3, 4, and 13.

---

## 8. Architecture Diagram

<img width="900" height="572" alt="image" src="https://github.com/user-attachments/assets/7430ffdc-1633-490a-a829-cd664293bac4" />



---
## 8. FrameWork Diagram

<img width="900" height="846" alt="image" src="https://github.com/user-attachments/assets/3d9251c9-f05d-421e-873a-4d66fbc4c62d" />


---

## 9. Dataset Details

| Field | Detail |
|---|---|
| Dataset Name | Synthetic EHR Storage & Access Log Dataset (self-generated), supplemented by public reference datasets for benchmarking |
| Source | Generated by the project team using a Python script modeled on access/growth patterns described in the reviewed literature (Papers 2, 9, 12, 13); optionally benchmarked against MIMIC-III (used in Paper 3) for realistic healthcare record structure |
| URL | Not publicly hosted for the synthetic portion; MIMIC-III available via PhysioNet ([physionet.org/content/mimiciii](https://physionet.org/content/mimiciii/)) under a credentialed data-use agreement |
| Size | Approx. 10,000–20,000 simulated backup/access events, scalable for training |
| Number of Records | ~15,000 (target), covering multiple simulated backup cycles |
| Number of Features | 8–10 (timestamp, record type, department, data size/volume, access frequency, criticality tag, backup status, storage tier, patient/staff role) |
| Data Type | Structured tabular time-series data (CSV/JSON) |
| License | Synthetic data: no license restrictions (no real patient information). If MIMIC-III is used for benchmarking: PhysioNet Credentialed Health Data License |
| Purpose | Train and validate the LSTM forecasting model for backup-demand prediction, and evaluate the prioritization/scheduling logic against ground-truth criticality labels |
| Preprocessing Required | Timestamp parsing into time-series windows (hourly/daily), normalization of storage-volume features, categorical encoding of department/record-type/criticality fields, and train/validation/test split for time-series forecasting |

---

## 10. AWS Services Plan

| AWS Service | Purpose |
|---|---|
| Amazon S3 (with Intelligent-Tiering / Glacier) | Tiered storage for EHR backups — hot data in Standard, cold/archival data auto-moved to IA/Glacier based on predicted access frequency |
| AWS Lambda | Triggers backup jobs automatically based on model predictions and new-data events |
| Amazon SageMaker | Trains and hosts the LSTM predictive model for backup-demand and storage-growth forecasting |
| AWS Step Functions | Orchestrates the end-to-end pipeline: forecast → prioritize → schedule → execute backup → verify |
| Amazon RDS | Stores backup metadata, logs, and audit trail (what was backed up, when, priority tier) |
| Amazon DynamoDB | Fast lookup store for record-criticality tags and scheduling state |
| Amazon CloudWatch | Monitors pipeline health, backup job success/failure, and triggers alerts on anomalies |
| Amazon SNS | Sends notifications/alerts for backup failures or missed critical-data windows |
| Amazon QuickSight | Dashboard visualizing predicted vs. actual backup demand, storage cost trends, and backup success rates |
| AWS IAM | Enforces least-privilege access control across all services |
| Amazon Cognito | Authenticates hospital admin/IT staff accessing the monitoring dashboard |
| AWS Backup | Central backup management/orchestration layer integrating with S3, RDS, and DynamoDB backup policies |

---

## 11. Technology Stack

- **Python** — core language for data preprocessing, model training, and AWS service integration
- **TensorFlow / PyTorch (Keras API)** — building and training the LSTM/time-series forecasting model
- **Scikit-learn** — baseline models, feature engineering, evaluation metrics (RMSE, MAE, accuracy)
- **Pandas / NumPy** — data preprocessing and time-series manipulation
- **Boto3** — Python SDK for interacting with AWS services (S3, Lambda, SageMaker, Step Functions, etc.)
- **AWS SDK / CLI** — deployment and infrastructure configuration
- **Matplotlib / Plotly (or QuickSight)** — visualization of forecasted vs. actual backup demand
- **Git / GitHub** — version control and team collaboration per the branch structure in the guidelines
- **Jupyter Notebook** — model development and experimentation environment
