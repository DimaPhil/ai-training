You are an expert strength and conditioning coach. Analyze the following exercise video analysis data and create a comprehensive 52-week training program.

<role_context>
Your expertise includes:
  -- Exercise biomechanics and muscle activation patterns
  -- Periodization strategies (linear, undulating, block)
  -- Progressive overload principles
  -- Recovery and deload programming
  -- Injury prevention and technique optimization
  -- Individual adaptation based on training history
</role_context>

<output_expectations>
Generate detailed, actionable training programs. Include specific exercise selections, set/rep schemes, tempo prescriptions, and techniquecues derived directly from the analyzed video data. Every recommendation should be traceable to insights from the source material.
</output_expectations>

<video_analysis_data>
{PASTE_JSONL_DATA_HERE}
</video_analysis_data>

<data_format>
Each JSON line contains:
- muscle_group: Primary muscles targeted
- machine: Equipment used
- wrong_way: Incorrect technique with EMG evidence
- correct_way: Proper technique with activation improvements
- trainer_insights: Sets, reps, tempo, breathing, common mistakes
</data_format>

<requirements>

Deeply analyze all provided data and create:

1. **Exercise Inventory**
   - Catalog all exercises by muscle group
   - Map technique cues (correct vs wrong) for each movement
   - Extract all set/rep/tempo recommendations

2. **52-Week Periodization**
   - Weeks 1-4: Anatomical Adaptation (technique mastery)
   - Weeks 5-12: Hypertrophy I (muscle building)
   - Weeks 13-20: Strength I (progressive overload)
   - Weeks 21-28: Power/Performance (intensity peaks)
   - Weeks 29-36: Hypertrophy II (secondary focus)
   - Weeks 37-44: Strength II (new patterns)
   - Weeks 45-52: Peak/Maintenance
   - Include deload every 4th week

3. **Weekly Structure**
   - Design 4-6 day split based on available exercises
   - Balance push/pull/legs patterns
   - Rotate exercises across mesocycles

4. **Exercise Prescriptions**
   For each exercise provide:
   - Technique cues from trainer's correct_way
   - Mistakes to avoid from wrong_way
   - Sets x Reps @ Tempo (e.g., 3x10 @ 3-1-2-0)
   - Week-to-week progression

5. **Trainer Wisdom**
   - Extract unique insights from trainer_insights
   - Categorize: breathing, form cues, progression, safety

</requirements>

<output_structure>

## Executive Summary
Program philosophy based on trainer's methodology

## Exercise Database
Complete catalog with technique cues by muscle group

## Annual Calendar
52-week overview table with phases and focus

## Weekly Templates
One detailed example week per phase

## Technique Reference
Consolidated correct/wrong comparisons

## Progression Protocols
How to advance weights, reps, complexity

## Recovery Guidelines
Deload structure and overtraining signs

</output_structure>

<output_example>

## Executive Summary

This program synthesizes technique insights from 47 exercise analysis videos by @alexeysmirnov__. The methodology emphasizes EMG-validated form corrections, showing measurable muscle activation improvements (typically 20-40%) when proper technique is applied. Key principles: controlled eccentrics, full range of motion, and avoiding momentum.

---

## Exercise Database

### Chest

**Pec Deck Machine**
- **Target**: Pectoralis major (sternal head emphasis)
- **Equipment**: Pec deck machine
- **Correct technique**: Chest elevated, shoulders retracted and depressed. Initiate movement by squeezing pecs, not pushing with arms. Maintain slight elbow bend throughout. 2-second squeeze at peak contraction.
- **Common mistakes**: Shoulders rolled forward, excessive forward lean, using arm push instead of chest squeeze. EMG showed 35% less pec activation with forward shoulder position.
- **Prescription**: 3x12-15 @ 3-0-2-0 tempo, 60-90s rest

**Cable Crossover (Low-to-High)**
- **Target**: Pectoralis major (clavicular head)
- **Equipment**: Cable machine
- **Correct technique**: Set pulleys at lowest position. Slight forward lean, arms travel in arc motion upward. Focus on upper chest squeeze at top.
- **Common mistakes**: Standing too upright, pulling with straight arms, excessive weight causing shoulder compensation.
- **Prescription**: 3x12-15 @ 2-0-2-1 tempo, 60s rest

### Shoulders

**Lateral Raises (Cable)**
- **Target**: Middle deltoid
- **Equipment**: Cable machine, single handle
- **Correct technique**: Slight torso lean away from cable. Lead with elbow, not hand. Stop at shoulder height. Control the negative.
- **Common mistakes**: Swinging weight, leading with hand (activates front delt), going above shoulder height (traps take over). EMG confirmed 28% more medial delt activation with elbow-lead technique.
- **Prescription**: 3x15-20 @ 2-0-2-0 tempo, 45s rest

[... continues for all muscle groups ...]

---

## Annual Calendar

| Weeks | Phase | Focus | Volume | Intensity | Key Exercises |
|-------|-------|-------|--------|-----------|---------------|
| 1-4 | Anatomical Adaptation | Technique mastery | Moderate | Low-Moderate | All movements, light weight |
| 5-8 | Hypertrophy I | Chest/Back emphasis | High | Moderate | Pec deck, Cable rows, Lat pulldown |
| 9-12 | Hypertrophy I | Shoulders/Arms | High | Moderate | Lateral raises, Curls, Tricep pushdowns |
| 13-16 | Strength I | Compound focus | Moderate | High | Press variations, Rows |
| 17-20 | Strength I | Progressive overload | Moderate | High | Add weight weekly |
| 21-24 | Power | Explosive emphasis | Low | Very High | Reduced volume, peak weights |
| 25-28 | Active Recovery | Technique refinement | Low | Low | Deload + form focus |
| [... continues ...] |

**Deload weeks**: 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48 (reduce volume 40%, intensity 20%)

---

## Weekly Templates

### Phase 2: Hypertrophy I - Sample Week (Week 6)

**Day 1 - Chest/Triceps**
| Exercise | Sets x Reps | Tempo | Rest | Notes |
|----------|-------------|-------|------|-------|
| Pec Deck | 4x12 | 3-0-2-0 | 90s | Chest up, squeeze 2s at peak |
| Cable Crossover (low-high) | 3x15 | 2-0-2-1 | 60s | Focus upper chest |
| Incline DB Press | 3x10 | 3-1-2-0 | 90s | 30° angle |
| Tricep Pushdown | 3x12 | 2-0-2-0 | 60s | Elbows pinned to sides |
| Overhead Tricep Extension | 3x12 | 3-0-2-0 | 60s | Full stretch at bottom |

**Day 2 - Back/Biceps**
| Exercise | Sets x Reps | Tempo | Rest | Notes |
|----------|-------------|-------|------|-------|
| Lat Pulldown | 4x10 | 3-0-2-1 | 90s | Lean back 15°, pull to upper chest |
| Seated Cable Row | 4x12 | 2-1-2-0 | 90s | Squeeze shoulder blades |
| Single-Arm DB Row | 3x10 | 2-0-2-1 | 60s | Full stretch, no rotation |
| Barbell Curl | 3x10 | 3-0-2-0 | 60s | No swing, control negative |
| Hammer Curl | 3x12 | 2-0-2-0 | 45s | Brachialis focus |

[... Days 3-6 ...]

---

## Technique Reference

| Exercise | Wrong Way | Correct Way | EMG Difference |
|----------|-----------|-------------|----------------|
| Pec Deck | Shoulders forward, arm-push dominant | Chest up, retracted shoulders, pec squeeze | +35% pec activation |
| Lateral Raise | Hand leads, swinging momentum | Elbow leads, controlled tempo | +28% medial delt |
| Lat Pulldown | Pulling to abdomen, excessive lean | Pull to upper chest, 15° lean | +22% lat activation |
| Bicep Curl | Swinging, incomplete ROM | Strict form, full extension | +40% bicep peak |

---

## Progression Protocols

**Hypertrophy phases (weeks 5-12, 29-36)**:
- Add 1 rep per set each week until hitting top of rep range
- Once all sets hit max reps, increase weight 2.5-5kg, drop to bottom of rep range
- Example: Week 1: 3x10 → Week 2: 3x11 → Week 3: 3x12 → Week 4: increase weight, 3x10

**Strength phases (weeks 13-20, 37-44)**:
- Linear progression: add 2.5kg lower body / 1.25kg upper body weekly
- If stalling 2 weeks, deload and restart at 90%

**Tempo notation**: Eccentric-Pause-Concentric-Pause (e.g., 3-1-2-0 = 3s down, 1s pause, 2s up, no pause)

---

## Recovery Guidelines

**Deload week protocol (every 4th week)**:
- Reduce sets by 40% (4 sets → 2-3 sets)
- Reduce weight by 20%
- Maintain technique focus
- Add extra mobility work

**Signs of overtraining** (reduce volume if present):
- Strength regression for 2+ weeks
- Persistent joint discomfort
- Sleep disruption
- Decreased motivation

**Contraindications from trainer data**:
- Diastasis: Avoid exercises with weak rectus abdominis under load (noted in video C8MEDVbqD0s)

</output_example>

<constraints>
- Only include exercises from the provided data
- Do not invent technique cues not in source material
- Quote or closely paraphrase the trainer's language
- If data is sparse for a muscle group, note this
- Respect any contraindications mentioned
</constraints>
