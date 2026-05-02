# AGENT_WORK_PROTOCOL.md

# Multi-Agent Collaboration Protocol

## 1. Purpose

This document defines the collaboration protocol for the multi-agent reconstruction project.

The protocol applies to all project stages, including V1, V2, Task 3.0, and later tasks.

Core principles:

```text
1. The Core Agent organizes tasks according to the current task list.
2. Each Subagent is responsible for exactly one functional module or one clearly bounded function.
3. Subagents submit measurable acceptance indicators before handing work to the Core Agent.
4. The Core Agent validates the project by running the full workflow after all Subagents finish.
5. Failed files or failed modules must be traced back to the responsible Subagent for modification.
6. Chinese is used for internal work records.
7. English is used for inter-agent handover data in communication.md.
```

---

## 2. Environment Convention

All agents must use the existing Conda environment:

```text
3D_Reconstruction
```

Routine activation commands do not require permission:

```bash
source /home/lyx/miniconda3/etc/profile.d/conda.sh
conda activate 3D_Reconstruction
```

All Python package management should be performed inside this environment.

Agents must not create, delete, rename, or recreate the environment unless the Core Agent explicitly approves it.

---

## 3. Project Directory Convention

The project root is assumed to be:

```text
./
```

Input image data is stored in:

```text
./data/image/
```

Main output directories:

```text
./results/
./results/logs/
./agent_message/
./agent_message/agentwork_record/
```

Subagent communication files should be written under:

```text
./agent_message/communication/
```

Subagent work records should be written under:

```text
./agent_message/agentwork_record/
```

Recommended structure:

```text
./
├── data/
│   └── image/
│
├── results/
│   ├── sparse/
│   ├── dense/
│   ├── mesh/
│   ├── visualization/
│   └── logs/
│
├── agent_message/
│   ├── communication/
│   │   ├── subagent_x_communication.md
│   │   └── ...
│   └── agentwork_record/
│       ├── core_agent_record.md
│       ├── subagent_work_record.md
│       └── ...
│
├── config.yaml
└── tasklist files
```

If a required directory does not exist, the responsible agent should create it.

---

## 4. Core Agent Responsibilities

The Core Agent is responsible for organization, coordination, integration, and final workflow validation.

The Core Agent must:

```text
1. Read the current task list before assigning work.
2. Read existing agent records before organizing a new round of work.
3. Inspect the current project file structure.
4. Split the current task list into functional modules.
5. Assign each functional module to one corresponding Subagent.
6. Ensure one Subagent is responsible for one function or one clearly bounded module.
7. Provide each Subagent with:
   - task objective
   - input files
   - expected output files
   - acceptance indicators
   - required communication file path
8. Collect each Subagent's submitted acceptance indicator checklist.
9. Check whether each Subagent's communication.md is compliant.
10. After all Subagents finish, run the full workflow once to confirm the project is usable.
11. If the full workflow fails, locate the failing file or module.
12. Trace the failing file or module to the responsible Subagent.
13. Return the problem to the responsible Subagent for modification.
14. Accept final submission only after all acceptance indicators are satisfied.
15. Write the Core Agent work record after completing coordination and validation.
```

The Core Agent should not judge Subagent completion by re-reading every implementation detail unless necessary.

Routine acceptance should be based on:

```text
1. Whether the Subagent's metric checklist is complete.
2. Whether required output files exist.
3. Whether communication.md follows the required format.
4. Whether the full workflow runs successfully after all Subagents finish.
```

The Core Agent may inspect code deeply only when:

```text
1. The full workflow fails.
2. Output files are missing or invalid.
3. The Subagent's metrics contradict actual output.
4. The implementation appears to modify unrelated modules.
```

---

## 5. Subagent Responsibilities

Each Subagent is responsible for one functional module assigned by the Core Agent.

Each Subagent must:

```text
1. Read the current task list.
2. Read this protocol.
3. Read relevant previous agent records.
4. Inspect the files related to its assigned function.
5. Implement only its assigned functional module.
6. Avoid modifying unrelated modules unless necessary.
7. Use the existing 3D_Reconstruction Conda environment.
8. Run the required scripts or tests for its own module.
9. Check whether its assigned acceptance indicators are satisfied before submission.
10. Write a Chinese work record after finishing.
11. Write English handover data into communication.md.
12. Submit outputs to the Core Agent only after its own acceptance indicators are satisfied.
```

A Subagent should not claim completion if:

```text
1. Required output files are missing.
2. Required metrics are not produced.
3. The module cannot run.
4. communication.md is missing.
5. The work record is missing.
6. The acceptance checklist is incomplete.
```

---

## 6. One Subagent, One Function Rule

Task assignment must follow this rule:

```text
One Subagent corresponds to one function.
```

Examples:

```text
Subagent A: point cloud statistics
Subagent B: invalid point removal
Subagent C: statistical and radius outlier removal
Subagent D: DBSCAN main-cluster extraction
Subagent E: before/after visualization
Subagent F: cleaning report generation
```

A Subagent may write multiple files only if those files serve the same function.

A Subagent should not implement multiple unrelated functions in one round unless the Core Agent explicitly assigns them as one integrated module.

---

## 7. Subagent Acceptance Indicator Checklist

Before submitting to the Core Agent, each Subagent must produce a checklist.

The checklist should include:

```text
1. Assigned function name
2. Input files used
3. Output files generated
4. Commands executed
5. Program execution status
6. Quantitative metrics
7. Whether each task-list acceptance indicator is satisfied
8. Known limitations
9. Files modified
10. Files created
```

The checklist must be written in Chinese and included in the Subagent work record.

Example:

```markdown
## 验收指标清单

| 指标 | 结果 | 状态 |
|---|---|---|
| 是否成功读取 dense.ply | 成功读取 88561 点 | PASS |
| 是否删除 NaN/Inf | 删除 0 个无效点 | PASS |
| 是否输出 cleaned 文件 | results/mesh/dense_cleaned.ply | PASS |
```

---

## 8. communication.md Requirement

Each Subagent must write a communication file for data handover.

Location:

```text
./agent_message/communication/
```

Recommended filename:

```text
subagent_<id>_communication.md
```

or, when task-specific naming is clearer:

```text
task3_0_<function_name>_communication.md
```

The communication file must be written in English.

It should contain only data that other Subagents or the Core Agent need.

Required sections:

```markdown
# Communication

## Producer
Subagent name and function name.

## Files Produced
List of output files and their meaning.

## Data Format
Explain file format, fields, units, and coordinate assumptions.

## Metrics
Key quantitative results.

## How to Use
Instructions for downstream agents.

## Dependencies
Required files, libraries, and environment assumptions.

## Known Issues
Limitations or warnings for downstream agents.
```

The Core Agent must check whether each communication.md is compliant.

---

## 9. Work Record Requirement

All Subagents must write work records in Chinese.

The Subagent record should be placed under:

```text
./agent_message/agentwork_record/
```

For multiple Subagents in one task round, use one shared Subagent document unless the Core Agent assigns otherwise:

```text
./agent_message/agentwork_record/subagent_work_record.md
```

Each Subagent appends its own section:

```markdown
# Subagent Work Record

## Subagent A — Function Name

### 1. 工作内容记录（中文）
...

### 2. 程序执行结果（中文）
...

### 3. 验收指标清单（中文）
...
```

The work record must include:

```text
1. Agent name
2. Assigned function
3. Work content in Chinese
4. Files read
5. Files modified
6. Files created
7. Commands executed
8. Program execution result in Chinese
9. Acceptance indicator checklist in Chinese
10. Known problems in Chinese
```

---

## 10. Core Agent Record Requirement

The Core Agent must write its own record after completing coordination and final validation.

Recommended path:

```text
./agent_message/agentwork_record/core_agent_record.md
```

The Core Agent record must include:

```text
1. Task list used
2. Subagents assigned
3. Function assigned to each Subagent
4. Whether each Subagent submitted its metric checklist
5. Whether each communication.md is compliant
6. Full workflow command executed
7. Full workflow result
8. Failed files or modules, if any
9. Subagents asked to revise, if any
10. Final acceptance status
```

---

## 11. Full Workflow Validation

After all Subagents finish, the Core Agent must run the full workflow once.

The workflow command depends on the current task list.

For Task 3.0, an example full workflow may be:

```bash
source /home/lyx/miniconda3/etc/profile.d/conda.sh
conda activate 3D_Reconstruction
python main_task3_0.py --config config.yaml
```

The Core Agent must verify:

```text
1. The script runs without fatal errors.
2. Required output files exist.
3. Output files can be opened or parsed.
4. Required metrics are present.
5. The final acceptance criteria are satisfied.
```

If the full workflow fails, the Core Agent must:

```text
1. Identify the error message.
2. Identify the failed file.
3. Identify the module that created or modified the failed file.
4. Identify the responsible Subagent.
5. Return the issue to that Subagent for correction.
6. Re-run the full workflow after correction.
```

---

## 12. File Ownership and Failure Tracing

Every Subagent must report all created and modified files in its work record.

The Core Agent must use this information to trace failures.

If a file causes a failure:

```text
1. Find which Subagent created or modified it.
2. Assign the bug fix to that Subagent.
3. The Subagent must fix the issue.
4. The Subagent must update its work record and communication.md if the interface changes.
```

A Subagent should not modify another Subagent's owned file unless:

```text
1. The Core Agent assigns the fix to that Subagent.
2. The affected interface is documented in communication.md.
3. The modification is recorded in the work record.
```

---

## 13. Permission Rules

Agents should not ask for permission for routine operations.

Routine operations that do not require permission include:

```text
1. Running source to activate Conda.
2. Activating the existing 3D_Reconstruction environment.
3. Reading project files.
4. Editing assigned project source files.
5. Creating normal project directories.
6. Writing logs.
7. Writing work records.
8. Writing communication.md files.
9. Running ordinary Python scripts for the assigned task.
10. Installing clearly required common Python packages inside 3D_Reconstruction.
```

Agents should ask for permission when:

```text
1. An operation could be harmful to the system or project.
2. An operation might take a very long time to run.
3. The result is uncertain or unpredictable.
4. Deleting large directories or important project files.
5. Overwriting major result files without backup.
6. Changing the Conda environment name.
7. Removing or recreating the existing Conda environment.
8. Installing system-level packages with sudo.
9. Running commands that may modify system configuration.
10. Downloading large external datasets or models.
```

---

## 14. Submission Rule

A Subagent may submit work to the Core Agent only after:

```text
1. Its assigned function has been implemented.
2. Required output files have been generated.
3. Its acceptance indicators are satisfied.
4. Its Chinese work record has been written.
5. Its English communication.md has been written.
6. It has listed all files created and modified.
```

The Core Agent may accept final project submission only after:

```text
1. All Subagents have submitted their work.
2. All Subagent acceptance checklists are complete.
3. All communication.md files are compliant.
4. The full workflow has been executed.
5. The full workflow is usable.
6. Any failed module has been returned to the responsible Subagent and fixed.
7. The Core Agent record has been written.
```

---

## 15. Task 3.0 Specific Notes

For Task 3.0, the main goal is:

```text
Dense point cloud quality check and cleaning.
```

The Core Agent should divide Task 3.0 into functional Subagents according to the task list.

Possible functions:

```text
1. Dense point cloud loading and statistics
2. Invalid point removal
3. Statistical and radius outlier removal
4. DBSCAN main-cluster extraction
5. Optional color/background filtering
6. Voxel downsampling and normal estimation
7. Before/after visualization
8. Cleaning report generation
9. Full pipeline integration
```

Each function should correspond to one Subagent unless the Core Agent explicitly merges functions for practical reasons.

Task 3.0 must not proceed to Mesh reconstruction unless the task list explicitly says so.

Required final output for Task 3.0 should include:

```text
results/mesh/dense_cleaned.ply
results/mesh/cleaning_report.txt
results/mesh/pointcloud_before_after.png
```

Final acceptance depends on the current task list, but at minimum:

```text
1. dense_cleaned.ply exists.
2. dense_cleaned.ply can be opened.
3. cleaning_report.txt exists.
4. before/after visualization exists.
5. The full Task 3.0 workflow runs successfully.
```
