## 2. Two-layer recall audit
Corpus: 3950 papers (since-2000). Keyword-gate recall **99.6%**; venue coverage **92.3%**.

| Outcome | n | % |
|---|---|---|
| caught | 3635 | 92.0% |
| venue-gap | 299 | 7.6% |
| keyword-gap | 12 | 0.3% |
| both-gap | 4 | 0.1% |

**Calibration:** 91.5% of the 200 actually-reported papers are keyword-caught (target ≥90%).

Reported-but-not-keyword-caught (sample):
- LongCrafter: Towards Diverse Long-Context Understanding via Evidence-Graph-Guided Instruction Synthesis
- Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents
- Scoped Verification for Reliable Long-Horizon Agentic Context Evolution under Distribution Shift (GRACE)
- Remembering Distinct Items, Not Tokens: A Learnable Dirichlet-Process Cache Between State-Space Models and Attention
- From Self-Attention to Connection Laplacian: A Unified Operator View of Transformers
- Track, Rank, Crack: Epistemic Working Memory Scales Multi-Hop Reasoning
- The Refusal Residue: When Probes Catch Alignment Faking and When They Don't
- What Models Express, Suppress, and Resist: Auditing Open-Weight LLMs with Persona Vectors

## 4. Venue calibration
Papers failing the venue gate after the 2026-08-01 expansion (journals 47→66, direct-scan 10→16, ACL/CVPR proceedings added):

- **journal:PsycEXTRA Dataset [title-match, score=1.0]**: 8 paper(s)
- **journal:Cognitive, Affective, &amp; Behavioral Neuroscience [title-match, score=1.0]**: 7 paper(s)
- **journal:The Hippocampus from Cells to Systems [NOT-listed]**: 3 paper(s)
- **journal:Predictions in the Brain [title-match, score=1.0]**: 3 paper(s)
- **journal:Proceedings of the AAAI Conference on Artificial Intelligence [title-match, score=1.0]**: 3 paper(s)
- **journal:Journal of Open Source Software [NOT-listed]**: 3 paper(s)
- **journal:Journal of Dementia and Alzheimer's Disease [title-match, score=1.0]**: 2 paper(s)
- **journal:Neuropsychopharmacology [NOT-listed]**: 2 paper(s)
- **journal:Journal of Medical Internet Research [title-match, score=1.0]**: 2 paper(s)
- **journal:The Journal of Prevention of Alzheimer's Disease [title-match, score=1.0]**: 2 paper(s)
- **journal:Oxford Handbooks Online [title-match, score=1.0]**: 2 paper(s)
- **journal:Advances in Science, Technology &amp; Innovation [title-match, score=1.0]**: 2 paper(s)
- **journal:DIGITAL HEALTH [title-match, score=1.0]**: 2 paper(s)
- **journal:Cognitive, Affective, &amp; Behavioral Neuroscience [NOT-listed]**: 2 paper(s)
- **journal:Journal of Artificial Intelligence Research [title-match, score=1.0]**: 2 paper(s)
- **journal:WIREs Cognitive Science [NOT-listed]**: 2 paper(s)
- **journal:Child Development [title-match, score=1.0]**: 2 paper(s)
- **journal:The Annals of Applied Statistics [NOT-listed]**: 2 paper(s)
- **journal:PNAS Nexus [NOT-listed]**: 2 paper(s)
- **journal:Nature Physics [NOT-listed]**: 2 paper(s)
- **journal:Annual Review of Vision Science [NOT-listed]**: 2 paper(s)
- **journal:Proceedings of the Twenty-Sixth International Joint Conference on Artificial Intelligence [title-match, score=1.0]**: 2 paper(s)
- **journal:Social Cognitive and Affective Neuroscience [NOT-listed]**: 2 paper(s)
- **journal:Interspeech 2021 [title-match, score=1.0]**: 2 paper(s)
- **journal:Cognitive Computation [title-match, score=1.0]**: 2 paper(s)
- **journal:Nature Biotechnology [NOT-listed]**: 2 paper(s)
- **journal:Journal of the Experimental Analysis of Behavior [title-match, score=1.0]**: 2 paper(s)
- **journal:Proceedings of the 23rd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining [title-match, score=1.0]**: 2 paper(s)
- **journal:Annals of Neurology [NOT-listed]**: 2 paper(s)
- **journal:Graph Neural Networks: Foundations, Frontiers, and Applications [title-match, score=0.891]**: 2 paper(s)
- **journal:Information Fusion [title-match, score=1.0]**: 1 paper(s)
- **journal:Theory and Society [NOT-listed]**: 1 paper(s)
- **journal:Journal of the Royal Society of New Zealand [NOT-listed]**: 1 paper(s)
- **journal:PLOS Digital Health [NOT-listed]**: 1 paper(s)
- **journal:BMJ [title-match, score=1.0]**: 1 paper(s)
- **journal:2016 IEEE International Conference on Big Data (Big Data) [title-match, score=1.0]**: 1 paper(s)
- **journal:Neurobiology of Attention [title-match, score=0.925]**: 1 paper(s)
- **journal:Foundations of Computational Mathematics [NOT-listed]**: 1 paper(s)
- **journal:Progress in Neurobiology [NOT-listed]**: 1 paper(s)
- **journal:2017 12th International Workshop on Self-Organizing Maps and Learning Vector Quantization, Clustering and Data Visualization (WSOM) [title-match, score=0.889]**: 1 paper(s)
- **journal:Frontiers in Physiology [NOT-listed]**: 1 paper(s)
- **journal:Cold Spring Harbor Perspectives in Biology [title-match, score=1.0]**: 1 paper(s)
- **journal:IEEE Transactions on Neural Systems and Rehabilitation Engineering [title-match, score=1.0]**: 1 paper(s)
- **journal:npj Digital Medicine [NOT-listed]**: 1 paper(s)
- **journal:Journal of the American Statistical Association [NOT-listed]**: 1 paper(s)
- **journal:Music Perception [title-match, score=1.0]**: 1 paper(s)
- **journal:IEEE Transactions on Neural Networks and Learning Systems [title-match, score=1.0]**: 1 paper(s)
- **journal:Control of Cognitive Processes [title-match, score=1.0]**: 1 paper(s)
- **journal:Statistical Science [title-match, score=1.0]**: 1 paper(s)
- **journal:Royal Society Open Science [NOT-listed]**: 1 paper(s)
- **journal:Philosophy of Science [NOT-listed]**: 1 paper(s)
- **journal:Neural Horizons The Uncharted Future of Deep Learning [title-match, score=0.974]**: 1 paper(s)
- **journal:Journal of Clinical and Experimental Neuropsychology [NOT-listed]**: 1 paper(s)
- **journal:American Economic Review [NOT-listed]**: 1 paper(s)
- **journal:Ageing Research Reviews [title-match, score=0.929]**: 1 paper(s)
- **journal:Proceedings of the British Machine Vision Conference 2014 [title-match, score=1.0]**: 1 paper(s)
- **journal:2014 IEEE International Workshop on Machine Learning for Signal Processing (MLSP) [title-match, score=1.0]**: 1 paper(s)
- **journal:Proceedings of the Royal Society B: Biological Sciences [title-match, score=1.0]**: 1 paper(s)
- **journal:Proceedings of SSST-8, Eighth Workshop on Syntax, Semantics and Structure in Statistical Translation [title-match, score=1.0]**: 1 paper(s)
- **journal:Sustainable Cities and Society [title-match, score=0.963]**: 1 paper(s)
- **journal:Age and Ageing [NOT-listed]**: 1 paper(s)
- **journal:Physical Review E [NOT-listed]**: 1 paper(s)
- **journal:Neurocase [title-match, score=1.0]**: 1 paper(s)
- **journal:Proceedings of the 2019 ACL Workshop BlackboxNLP: Analyzing and Interpreting Neural Networks for NLP [title-match, score=1.0]**: 1 paper(s)
- **journal:Proceedings of the twenty-fourth annual symposium on Computational geometry [title-match, score=1.0]**: 1 paper(s)
- **journal:Meta-Psychology [NOT-listed]**: 1 paper(s)
- **journal:Alcoholism: Clinical and Experimental Research [title-match, score=1.0]**: 1 paper(s)
- **journal:International Psychogeriatrics [NOT-listed]**: 1 paper(s)
- **journal:Progress in Brain Research [title-match, score=0.929]**: 1 paper(s)
- **journal:Memory Studies [NOT-listed]**: 1 paper(s)
- **journal:Random Structures &amp; Algorithms [NOT-listed]**: 1 paper(s)
- **journal:Psychology [NOT-listed]**: 1 paper(s)
- **journal:IEEE Transactions on Neural Networks [title-match, score=1.0]**: 1 paper(s)
- **journal:Multivariate Behavioral Research [NOT-listed]**: 1 paper(s)
- **journal:IEEE Signal Processing Magazine [title-match, score=1.0]**: 1 paper(s)
- **journal:Journal of Neuropsychology [NOT-listed]**: 1 paper(s)
- **journal:International Journal of Obesity [title-match, score=1.0]**: 1 paper(s)
- **journal:Brain and Behavior [NOT-listed]**: 1 paper(s)
- **journal:Finance Research Letters [title-match, score=1.0]**: 1 paper(s)
- **journal:HFSP Journal [NOT-listed]**: 1 paper(s)
- **journal:2025 IEEE International Conference on Robotics and Automation (ICRA) [title-match, score=0.857]**: 1 paper(s)
- **journal:Brain and Language [title-match, score=1.0]**: 1 paper(s)
- **journal:Frontiers in Robotics and AI [title-match, score=0.945]**: 1 paper(s)
- **journal:Biological Theory [title-match, score=1.0]**: 1 paper(s)
- **journal:Journal of the Medical Library Association [NOT-listed]**: 1 paper(s)
- **journal:Molecular Psychiatry [NOT-listed]**: 1 paper(s)
- **journal:Human Brain Function [title-match, score=1.0]**: 1 paper(s)
- **journal:Experimental Aging Research [NOT-listed]**: 1 paper(s)
- **journal:Journal of Experimental Social Psychology [title-match, score=1.0]**: 1 paper(s)
- **journal:2019 18th IEEE International Conference On Machine Learning And Applications (ICMLA) [title-match, score=1.0]**: 1 paper(s)
- **journal:9th International Conference on Artificial Neural Networks: ICANN '99 [title-match, score=1.0]**: 1 paper(s)
- **journal:Learning &amp; Behavior [title-match, score=1.0]**: 1 paper(s)
- **journal:Cognitive Neuropsychiatry [NOT-listed]**: 1 paper(s)
- **journal:Progress in Neurobiology [title-match, score=1.0]**: 1 paper(s)
- **journal:SpringerReference [title-match, score=0.899]**: 1 paper(s)
- **journal:PeerJ [NOT-listed]**: 1 paper(s)
- **journal:BMC Proceedings [title-match, score=1.0]**: 1 paper(s)
- **journal:Machine Learning under Malware Attack [title-match, score=1.0]**: 1 paper(s)
- **journal:Physics of Life Reviews [title-match, score=1.0]**: 1 paper(s)
- **journal:Computers in Biology and Medicine [title-match, score=1.0]**: 1 paper(s)
- **journal:AI Magazine [title-match, score=1.0]**: 1 paper(s)
- **journal:Humanities and Social Sciences Communications [NOT-listed]**: 1 paper(s)
- **journal:Journal of Neurochemistry [title-match, score=1.0]**: 1 paper(s)
- **journal:IBRO Neuroscience Reports [title-match, score=1.0]**: 1 paper(s)
- **journal:Journal of Neural Engineering [title-match, score=1.0]**: 1 paper(s)
- **journal:Sensors [NOT-listed]**: 1 paper(s)
- **journal:Interspeech 2019 [title-match, score=1.0]**: 1 paper(s)
- **journal:Projections [title-match, score=1.0]**: 1 paper(s)
- **journal:Social Neuroscience [title-match, score=0.938]**: 1 paper(s)
- **journal:Social Neuroscience [title-match, score=0.948]**: 1 paper(s)
- **journal:Frontiers in Aging Neuroscience [NOT-listed]**: 1 paper(s)
- **journal:Journal of Child Language [NOT-listed]**: 1 paper(s)
- **journal:Behavioral Neuroscience [title-match, score=1.0]**: 1 paper(s)
- **journal:Encyclopedia of Computational Neuroscience [title-match, score=1.0]**: 1 paper(s)
- **journal:Journal of the Optical Society of America A [title-match, score=1.0]**: 1 paper(s)
- **journal:PLoS Medicine [title-match, score=1.0]**: 1 paper(s)
- **journal:Neurology [title-match, score=1.0]**: 1 paper(s)
- **journal:BMC Neuroscience [title-match, score=1.0]**: 1 paper(s)
- **journal:The Clinical Neuropsychologist [NOT-listed]**: 1 paper(s)
- **journal:2018 17th IEEE International Conference on Machine Learning and Applications (ICMLA) [title-match, score=1.0]**: 1 paper(s)
- **journal:Psychological Research [NOT-listed]**: 1 paper(s)
- **journal:The Journal of Chemical Physics [NOT-listed]**: 1 paper(s)
- **journal:The Innovation [NOT-listed]**: 1 paper(s)
- **journal:SSRN Electronic Journal [title-match, score=1.0]**: 1 paper(s)
- **journal:CRAN: Contributed Packages [title-match, score=0.879]**: 1 paper(s)
- **journal:Cambridge Explorations in Arts and Sciences [title-match, score=1.0]**: 1 paper(s)
- **journal:BioMed Research International [title-match, score=1.0]**: 1 paper(s)
- **journal:npj Quantum Materials [NOT-listed]**: 1 paper(s)
- **journal:Social Cognition [title-match, score=0.916]**: 1 paper(s)
- **journal:SIAM Review [NOT-listed]**: 1 paper(s)
- **journal:Physiology [title-match, score=1.0]**: 1 paper(s)
- **journal:Physical Review X [title-match, score=1.0]**: 1 paper(s)
- **journal:Communications of the ACM [title-match, score=1.0]**: 1 paper(s)
- **journal:Philosophical Transactions of the Royal Society A: Mathematical, Physical and Engineering Sciences [NOT-listed]**: 1 paper(s)
- **journal:Aphasiology [NOT-listed]**: 1 paper(s)
- **journal:South African Journal of Psychology [NOT-listed]**: 1 paper(s)
- **journal:Behavioural Brain Research [title-match, score=1.0]**: 1 paper(s)
- **journal:Documenta Mathematica Series [title-match, score=1.0]**: 1 paper(s)
- **journal:International Journal of Computer Network and Information Security [title-match, score=0.863]**: 1 paper(s)
- **journal:Nature Reviews Physics [title-match, score=1.0]**: 1 paper(s)
- **journal:Bayesian Reasoning and Machine Learning [title-match, score=0.872]**: 1 paper(s)
- **journal:Journal of Internal Medicine [NOT-listed]**: 1 paper(s)
- **journal:Journal of Neurolinguistics [title-match, score=1.0]**: 1 paper(s)
- **journal:Eng [NOT-listed]**: 1 paper(s)
- **journal:Epilepsia [NOT-listed]**: 1 paper(s)
- **journal:Proceedings of the 2018 EMNLP Workshop BlackboxNLP: Analyzing and Interpreting Neural Networks for NLP [title-match, score=1.0]**: 1 paper(s)
- **journal:KI - Künstliche Intelligenz [NOT-listed]**: 1 paper(s)
- **journal:Inhibition in cognition. [title-match, score=1.0]**: 1 paper(s)
- **journal:Interspeech 2020 [title-match, score=1.0]**: 1 paper(s)
- **journal:Frontiers in Computer Science [title-match, score=1.0]**: 1 paper(s)
- **journal:2017 International Workshop on Pattern Recognition in Neuroimaging (PRNI) [title-match, score=1.0]**: 1 paper(s)
- **journal:Canadian Journal of Experimental Psychology / Revue canadienne de psychologie expérimentale [title-match, score=1.0]**: 1 paper(s)
- **journal:2014 International Workshop on Pattern Recognition in Neuroimaging [title-match, score=1.0]**: 1 paper(s)
- **journal:Advances in Physiology Education [title-match, score=1.0]**: 1 paper(s)
- **journal:Aging &amp; Mental Health [title-match, score=1.0]**: 1 paper(s)
- **journal:The Handbook of Language Emergence [title-match, score=1.0]**: 1 paper(s)
- **journal:First Language [NOT-listed]**: 1 paper(s)
- **journal:Biological Psychiatry: Cognitive Neuroscience and Neuroimaging [NOT-listed]**: 1 paper(s)
- **journal:Neuroimage: Reports [title-match, score=1.0]**: 1 paper(s)
- **journal:F1000Research [NOT-listed]**: 1 paper(s)
- **journal:Electronic Imaging [title-match, score=1.0]**: 1 paper(s)
- **journal:Brain Stimulation [title-match, score=1.0]**: 1 paper(s)
- **journal:Journal of Anatomy [title-match, score=0.979]**: 1 paper(s)
- **journal:2018 IEEE International Conference on Robotics and Automation (ICRA) [title-match, score=1.0]**: 1 paper(s)
- **journal:Neurology [NOT-listed]**: 1 paper(s)
- **journal:Proceedings of The 20th SIGNLL Conference on Computational Natural Language Learning [title-match, score=1.0]**: 1 paper(s)
- **journal:Sensors [title-match, score=1.0]**: 1 paper(s)
- **journal:2019 IEEE International Conference on Prognostics and Health Management (ICPHM) [title-match, score=1.0]**: 1 paper(s)
- **journal:Neural Processing Letters [title-match, score=0.945]**: 1 paper(s)
- **journal:Journal of Theoretical Biology [title-match, score=1.0]**: 1 paper(s)
- **journal:The Cambridge Handbook of Computational Cognitive Sciences [title-match, score=1.0]**: 1 paper(s)
- **journal:Current Opinion in Psychology [NOT-listed]**: 1 paper(s)
- **journal:Oxford Handbooks Online [NOT-listed]**: 1 paper(s)
- **journal:Perception [NOT-listed]**: 1 paper(s)
- **journal:Biocomputing 2018 [title-match, score=0.987]**: 1 paper(s)
- **journal:Biocomputing 2018 [title-match, score=1.0]**: 1 paper(s)
- **journal:Encyclopedia of Machine Learning [title-match, score=0.921]**: 1 paper(s)
- **journal:You and Your Lodger [title-match, score=1.0]**: 1 paper(s)
- **journal:Neurocase [NOT-listed]**: 1 paper(s)
- **journal:New England Journal of Medicine [NOT-listed]**: 1 paper(s)
- **journal:Proceedings of the Twenty-Sixth International Joint Conference on Artificial Intelligence [title-match, score=0.882]**: 1 paper(s)
- **journal:Statistical Applications in Genetics and Molecular Biology [NOT-listed]**: 1 paper(s)
- **journal:AIP Advances [NOT-listed]**: 1 paper(s)
- **journal:2017 55th Annual Allerton Conference on Communication, Control, and Computing (Allerton) [title-match, score=1.0]**: 1 paper(s)
- **journal:Nature Genetics [title-match, score=1.0]**: 1 paper(s)
- **journal:Journal of Physics: Conference Series [title-match, score=1.0]**: 1 paper(s)
- **journal:Science and Engineering Ethics [NOT-listed]**: 1 paper(s)
- **journal:British Journal of Psychology [NOT-listed]**: 1 paper(s)
- **journal:Encyclopedia of Perception [title-match, score=1.0]**: 1 paper(s)
- **journal:2008 46th Annual Allerton Conference on Communication, Control, and Computing [title-match, score=1.0]**: 1 paper(s)
- **journal:The Cognitive Neurosciences [title-match, score=1.0]**: 1 paper(s)
- **journal:Neuropsychology [title-match, score=1.0]**: 1 paper(s)
- **journal:Journal of Educational Psychology [NOT-listed]**: 1 paper(s)
- **journal:Brain Structure and Function [NOT-listed]**: 1 paper(s)
- **journal:Frontiers in Cellular Neuroscience [NOT-listed]**: 1 paper(s)
- **journal:Clinical Autonomic Research [title-match, score=1.0]**: 1 paper(s)
- **journal:The Journal of Mathematical Neuroscience [title-match, score=1.0]**: 1 paper(s)
- **journal:International Journal of Computer Vision [title-match, score=1.0]**: 1 paper(s)
- **journal:Brain and Cognition [title-match, score=1.0]**: 1 paper(s)
- **journal:Proceedings of the 2019 Conference of the North [title-match, score=0.948]**: 1 paper(s)
- **journal:Graphical Models [title-match, score=1.0]**: 1 paper(s)
- **journal:Dialogues in Clinical Neuroscience [title-match, score=1.0]**: 1 paper(s)
- **journal:Mental Processes in the Human Brain [title-match, score=1.0]**: 1 paper(s)
- **journal:Seismological Research Letters [title-match, score=1.0]**: 1 paper(s)
- **journal:2022 IEEE 25th International Conference on Computer Supported Cooperative Work in Design (CSCWD) [title-match, score=0.921]**: 1 paper(s)
- **journal:International Journal of Bifurcation and Chaos [title-match, score=1.0]**: 1 paper(s)
- **journal:2021 IEEE Winter Conference on Applications of Computer Vision (WACV) [title-match, score=1.0]**: 1 paper(s)
- **journal:BMC Psychiatry [title-match, score=0.972]**: 1 paper(s)
- **journal:Scientometrics [NOT-listed]**: 1 paper(s)
- **journal:2017 IEEE Winter Conference on Applications of Computer Vision (WACV) [title-match, score=1.0]**: 1 paper(s)
- **journal:Encyclopedia of Computational Neuroscience [NOT-listed]**: 1 paper(s)
- **journal:Journal of Autism and Developmental Disorders [NOT-listed]**: 1 paper(s)
- **journal:Proceedings of the Third BlackboxNLP Workshop on Analyzing and Interpreting Neural Networks for NLP [title-match, score=1.0]**: 1 paper(s)
- **journal:Frontiers in Robotics and AI [title-match, score=1.0]**: 1 paper(s)
- **journal:Connection Science [NOT-listed]**: 1 paper(s)
- **journal:Journal of Psychiatric Research [title-match, score=1.0]**: 1 paper(s)
- **journal:Neuromethods [NOT-listed]**: 1 paper(s)
- **journal:Neuroscience Research [title-match, score=1.0]**: 1 paper(s)
- **journal:Graduate Studies in Mathematics [title-match, score=1.0]**: 1 paper(s)
- **journal:Proceedings of the Eighth Workshop on Computational Linguistics and Clinical Psychology [title-match, score=1.0]**: 1 paper(s)
- **journal:ACM Computing Surveys [NOT-listed]**: 1 paper(s)
- **journal:The Making of Human Concepts [title-match, score=0.93]**: 1 paper(s)
- **journal:Molecular Neurodegeneration [NOT-listed]**: 1 paper(s)
- **journal:Automatica [title-match, score=0.886]**: 1 paper(s)
- **journal:The American Mathematical Monthly [NOT-listed]**: 1 paper(s)
- **journal:Frontiers in Dementia [NOT-listed]**: 1 paper(s)
- **journal:2017 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) [title-match, score=1.0]**: 1 paper(s)
- **journal:2018 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP) [title-match, score=1.0]**: 1 paper(s)
- **journal:IEEE Signal Processing Magazine [NOT-listed]**: 1 paper(s)
- **journal:Developmental Cognitive Neuroscience [NOT-listed]**: 1 paper(s)
- **journal:From Human Attention to Computational Attention [title-match, score=0.88]**: 1 paper(s)
- **journal:Acta Psychologica [title-match, score=1.0]**: 1 paper(s)
- **journal:The Cerebellum [NOT-listed]**: 1 paper(s)
- **journal:IEEE Journal of Selected Topics in Signal Processing [title-match, score=1.0]**: 1 paper(s)
- **journal:Foundations and Trends® in Machine Learning [NOT-listed]**: 1 paper(s)
- **journal:Journal of Neuroscience Methods [title-match, score=1.0]**: 1 paper(s)
- **journal:Springer Texts in Statistics [title-match, score=1.0]**: 1 paper(s)
- **journal:IEEE Transactions on Signal Processing [title-match, score=1.0]**: 1 paper(s)
- **journal:Logic Journal of IGPL [title-match, score=1.0]**: 1 paper(s)
- **journal:Child Maltreatment [NOT-listed]**: 1 paper(s)
- **journal:Psychological Research [title-match, score=1.0]**: 1 paper(s)
- **journal:Proceedings of the Eleventh ACM International Conference on Web Search and Data Mining [NOT-listed]**: 1 paper(s)
- **journal:Communications Engineering [NOT-listed]**: 1 paper(s)
- **journal:Physical Review B [title-match, score=1.0]**: 1 paper(s)
- **journal:2014 IEEE International Workshop on Machine Learning for Signal Processing (MLSP) [title-match, score=0.896]**: 1 paper(s)
- **journal:Journal of Neurophysiology [title-match, score=0.99]**: 1 paper(s)
- **journal:Robotics: Science and Systems XIV [title-match, score=1.0]**: 1 paper(s)
- **journal:Scholarpedia [NOT-listed]**: 1 paper(s)
- **journal:Psychocinematics [title-match, score=1.0]**: 1 paper(s)
- **journal:SpringerReference [title-match, score=0.93]**: 1 paper(s)
- **journal:Proceedings of the Twenty-Eighth International Joint Conference on Artificial Intelligence [title-match, score=1.0]**: 1 paper(s)
- **journal:Communications of the ACM [title-match, score=0.954]**: 1 paper(s)
- **journal:Molecular Physics [title-match, score=1.0]**: 1 paper(s)
- **journal:Communications of the ACM [NOT-listed]**: 1 paper(s)
- **journal:Brain Communications [title-match, score=1.0]**: 1 paper(s)
- **journal:PLOS Mental Health [title-match, score=0.945]**: 1 paper(s)
- **journal:Advanced Science [NOT-listed]**: 1 paper(s)
- **journal:Computational Psychiatry [title-match, score=1.0]**: 1 paper(s)

**Remaining gaps — recommended: do NOT add.** These are single papers in off-domain or low-yield venues (sociology, health-tech, general engineering); adding them would add scan cost without coverage value. Revisit if the library accumulates ≥2 papers from any of them.

**Tier 1 — ACTIVE journals to ADD to the source list** (≥2 library papers, ≥1 from 2020+):
- Cognitive, Affective, &amp; Behavioral Neuroscience (9 papers, 2002–2023)
- Communications of the ACM (3 papers, 2012–2021)
- Journal of Open Source Software (3 papers, 2018–2024)
- Journal of Dementia and Alzheimer's Disease (2 papers, 2021–2026)
- Journal of Medical Internet Research (2 papers, 2017–2025)
- The Journal of Prevention of Alzheimer's Disease (2 papers, 2017–2024)
- Progress in Neurobiology (2 papers, 2019–2020)
- Advances in Science, Technology &amp; Innovation (2 papers, 2021–2026)
- DIGITAL HEALTH (2 papers, 2022–2025)
- 2014 IEEE International Workshop on Machine Learning for Signal Processing (MLSP) (2 papers, 2014–2020)
- Journal of Artificial Intelligence Research (2 papers, 2017–2020)
- WIREs Cognitive Science (2 papers, 2021–2024)
- PNAS Nexus (2 papers, 2023–2024)
- Nature Physics (2 papers, 2018–2020)
- Social Cognitive and Affective Neuroscience (2 papers, 2019–2022)
- Sensors (2 papers, 2020–2024)
- Neurology (2 papers, 2016–2020)
- Interspeech 2021 (2 papers, 2021–2021)
- Nature Biotechnology (2 papers, 2019–2021)
- Annals of Neurology (2 papers, 2024–2024)

**Tier 1b — HISTORICAL ONLY (do NOT add to the daily scan)** (≥2 papers but none from 2020+ — likely dead/renamed venues):
- PsycEXTRA Dataset (8 papers, 2002–2014)
- The Hippocampus from Cells to Systems (3 papers, 2017–2017)
- Oxford Handbooks Online (3 papers, 2001–2017)
- Predictions in the Brain (3 papers, 2009–2009)
- Proceedings of the AAAI Conference on Artificial Intelligence (3 papers, 2015–2017)
- Proceedings of the Twenty-Sixth International Joint Conference on Artificial Intelligence (3 papers, 2016–2017)
- Neuropsychopharmacology (2 papers, 2011–2017)
- Neurocase (2 papers, 2001–2006)
- IEEE Signal Processing Magazine (2 papers, 2008–2012)
- Frontiers in Robotics and AI (2 papers, 2016–2017)
- Child Development (2 papers, 2004–2005)
- The Annals of Applied Statistics (2 papers, 2011–2011)
- Annual Review of Vision Science (2 papers, 2015–2016)
- SpringerReference (2 papers, 2001–2018)
- Social Neuroscience (2 papers, 2001–2001)
- Encyclopedia of Computational Neuroscience (2 papers, 2001–2013)
- Psychological Research (2 papers, 2000–2018)
- Cognitive Computation (2 papers, 2009–2015)
- Journal of the Experimental Analysis of Behavior (2 papers, 2005–2009)
- Proceedings of the 23rd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (2 papers, 2017–2017)
- Biocomputing 2018 (2 papers, 2018–2018)
- Graph Neural Networks: Foundations, Frontiers, and Applications (2 papers, 2016–2017)

**Tier 1c — single-paper venues (no recommendation, for reference):**
- Philosophical Transactions of the Royal Society A: Mathematical, Physical and Engineering Sciences (2026)
- Theory and Society (2025)
- Royal Society Open Science (2025)
- Age and Ageing (2025)
- Journal of Neuropsychology (2025)
- The Clinical Neuropsychologist (2025)
- Eng (2025)
- npj Digital Medicine (2024)
- Computers in Biology and Medicine (2024)
- Humanities and Social Sciences Communications (2024)
- The Innovation (2024)
- Advances in Physiology Education (2024)
- British Journal of Psychology (2024)
- Scientometrics (2024)
- Molecular Neurodegeneration (2024)

**Tier 2 — promote to direct-scan?** (listed in the 47 but not direct-scanned; shown with corpus paper counts — prefer venues with high library weight)
- Frontiers in Psychology (20 corpus paper(s))
- Psychological Review (10 corpus paper(s))
- PLOS Computational Biology (10 corpus paper(s))
- Topics in Cognitive Science (9 corpus paper(s))
- PLoS ONE (9 corpus paper(s))
- The Journal of Neuroscience (8 corpus paper(s))
- Cell Reports (8 corpus paper(s))
- Annual Review of Neuroscience (8 corpus paper(s))
- Philosophical Transactions of the Royal Society B: Biological Sciences (7 corpus paper(s))
- PLOS Biology (7 corpus paper(s))
- Cognitive Psychology (7 corpus paper(s))
- Frontiers in Human Neuroscience (7 corpus paper(s))
- Frontiers in Computational Neuroscience (6 corpus paper(s))
- PLOS ONE (6 corpus paper(s))
- Frontiers in Systems Neuroscience (6 corpus paper(s))
- NeuroImage (5 corpus paper(s))
- Behavior Research Methods (5 corpus paper(s))
- Current Directions in Psychological Science (5 corpus paper(s))
- Nature Reviews Psychology (5 corpus paper(s))
- PLoS Computational Biology (4 corpus paper(s))
- Nature Medicine (4 corpus paper(s))
- Frontiers in Neuroinformatics (4 corpus paper(s))
- eneuro (4 corpus paper(s))
- Physical Review Letters (4 corpus paper(s))
- npj Science of Learning (4 corpus paper(s))
- Cortex (4 corpus paper(s))
- Language, Cognition and Neuroscience (3 corpus paper(s))
- Consciousness and Cognition (3 corpus paper(s))
- Frontiers in Behavioral Neuroscience (3 corpus paper(s))
- Trends in Neurosciences (3 corpus paper(s))
- Cognition (3 corpus paper(s))
- Journal of Experimental Psychology: Learning, Memory, and Cognition (3 corpus paper(s))
- Frontiers in Neuroscience (3 corpus paper(s))
- Journal of Mathematical Psychology (3 corpus paper(s))
- Journal of Cognition (3 corpus paper(s))
- The Neuroscientist (3 corpus paper(s))
- Memory (2 corpus paper(s))
- Alzheimer's &amp; Dementia (2 corpus paper(s))
- Computational Brain &amp; Behavior (2 corpus paper(s))
- Nature Computational Science (2 corpus paper(s))
- Brain (2 corpus paper(s))
- Cognitive Neuropsychology (2 corpus paper(s))
- Cognitive Neuroscience (2 corpus paper(s))
- Neural Computation (2 corpus paper(s))
- Journal of Alzheimer's Disease (2 corpus paper(s))
- Perspectives on Psychological Science (2 corpus paper(s))
- iScience (2 corpus paper(s))
- Developmental Science (2 corpus paper(s))
- Psychology and Aging (2 corpus paper(s))
- Imaging Neuroscience (2 corpus paper(s))
- Nature Methods (2 corpus paper(s))
- Cognitive Research: Principles and Implications (2 corpus paper(s))
- Brain Sciences (1 corpus paper(s))
- Neurobiology of Learning and Memory (1 corpus paper(s))
- Behavioral and Brain Sciences (1 corpus paper(s))
- Neuropsychologia (1 corpus paper(s))
- Journal of Alzheimer’s Disease (1 corpus paper(s))
- Human Brain Mapping (1 corpus paper(s))
- Nature Protocols (1 corpus paper(s))
- Frontiers in Psychiatry (1 corpus paper(s))
- Journal of Experimental Psychology: Human Perception and Performance (1 corpus paper(s))
- Psychophysiology (1 corpus paper(s))
- Journal of Memory and Language (1 corpus paper(s))

**Tier 3 — arXiv categories to consider:**

## 5. Section distribution (by era)
| Section | Keywords | Total | 2000–09 | 2010–19 | 2020–26 |
|---|---|---|---|---|---|
| A — Human/Animal Systems & Cognitive Neu | 134 | 3756 | 438 | 1986 | 1332 |
| B — Computational Models of Memory | 58 | 2300 | 214 | 1275 | 811 |
| C — LLMs and Machine Memory | 50 | 246 | 3 | 69 | 174 |
| D — Encoding, Working Memory & Retrieval | 63 | 1113 | 99 | 638 | 376 |
| E — Naturalistic Paradigms & Neuroimagin | 43 | 1532 | 181 | 808 | 543 |
| F — Methods, Benchmarks & Meta-Science | 17 | 0 | 0 | 0 | 0 |
| G — Reinforcement Learning, Decision-Mak | 28 | 2287 | 225 | 1181 | 881 |

## 3. Miss mining & edit simulation
Misses: 16. Candidates: 80 shown (freq≥2, specificity≤60%, not already in matrix, **and rescuing ≥1 paper from 2020+** — scale-up recency filter).
Review = the **rescued papers**, not the keywords: drop any keyword whose rescued papers look off-topic.

| Keyword | Source | Freq | Spec | Section(s) | #rescued (≥2020) | Rescued papers (first 3)
|---|---|---|---|---|---|---|
| `independent` | ngram | 17 | 0.08 | A,G | 2 (1) | 2001 Topographic independent component analysis; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `cient` | ngram | 14 | 0.25 | A,B | 5 (1) | 2019 Neurocognitive Signatures of Naturalistic Reading of Scienti; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2013 Auto-Encoding Variational Bayes |
| `valine` | ngram | 13 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `amino` | ngram | 9 | 0.00 | A,B | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `hdac6` | ngram | 8 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `cell` | ngram | 8 | 0.13 | A,G | 4 (1) | 2006 Reducing the dimensionality of data with neural networks; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2015 Data-Driven Phenotypic Dissection of AML Reveals Progenitor- |
| `human` | ngram | 8 | 0.47 | A,G | 2 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2018 A Closed-form Solution to Photorealistic Image Stylization |
| `patient` | ngram | 7 | 0.06 | A,G | 3 (1) | 2002 The cognitive neuroscience of confabulation - A review and a; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2015 Data-Driven Phenotypic Dissection of AML Reveals Progenitor- |
| `functions` | ngram | 7 | 0.12 | A,B | 3 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2012 Cauchy and the gradient method; 2017 Recovery Guarantees for One-hidden-layer Neural Networks |
| `dna damage` | ngram | 6 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `damage` | ngram | 6 | 0.03 | A,G | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `remains` | ngram | 6 | 0.11 | A,G | 4 (1) | 2006 Reducing the dimensionality of data with neural networks; 2019 Neurocognitive Signatures of Naturalistic Reading of Scienti; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `specific` | ngram | 6 | 0.15 | A,G | 3 (1) | 2019 Neurocognitive Signatures of Naturalistic Reading of Scienti; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2014 Equitability, mutual information, and the maximal informatio |
| `intracellular` | ngram | 5 | 0.00 | A,E | 2 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2015 Data-Driven Phenotypic Dissection of AML Reveals Progenitor- |
| `driven` | ngram | 5 | 0.07 | A,B | 2 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2015 Data-Driven Phenotypic Dissection of AML Reveals Progenitor- |
| `underlying` | ngram | 5 | 0.14 | A,G | 3 (1) | 2002 The cognitive neuroscience of confabulation - A review and a; 2019 Neurocognitive Signatures of Naturalistic Reading of Scienti; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `even` | ngram | 5 | 0.40 | A,G | 5 (1) | 2002 The cognitive neuroscience of confabulation - A review and a; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2013 Auto-Encoding Variational Bayes |
| `sensed` | ngram | 4 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `human hdac6` | ngram | 4 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `amino acids` | ngram | 4 | 0.00 | A,B | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `acids` | ngram | 4 | 0.00 | A,D | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `amino acid` | ngram | 4 | 0.00 | A,B | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `to regulate` | ngram | 4 | 0.00 | A,G | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `acid` | ngram | 4 | 0.00 | A,B | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `regulate` | ngram | 4 | 0.01 | A,G | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `cellular` | ngram | 4 | 0.03 | A,G | 2 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2015 Data-Driven Phenotypic Dissection of AML Reveals Progenitor- |
| `the underlying` | ngram | 4 | 0.05 | A,B | 2 (1) | 2019 Neurocognitive Signatures of Naturalistic Reading of Scienti; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `directly` | ngram | 4 | 0.08 | A,G | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `local` | ngram | 4 | 0.09 | A,B | 2 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2017 Recovery Guarantees for One-hidden-layer Neural Networks |
| `identify` | ngram | 4 | 0.10 | A,G | 3 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2014 Equitability, mutual information, and the maximal informatio; 2019 Large-scale assessment of a smartwatch to identify atrial fi |
| `us to` | embedding | 4 | 0.10 | A,B | 4 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2013 Auto-Encoding Variational Bayes; 2013 Kingma |
| `signal` | ngram | 4 | 0.14 | A,G | 3 (1) | 2006 Reducing the dimensionality of data with neural networks; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2015 Data-Driven Phenotypic Dissection of AML Reveals Progenitor- |
| `remain` | ngram | 4 | 0.18 | A,G | 6 (1) | 2019 A structural probe for finding syntax in word representation; 2019 A structural probe for finding syntax in word representation; 2006 Reducing the dimensionality of data with neural networks |
| `identi` | ngram | 4 | 0.21 | A,G | 7 (1) | 2019 A structural probe for finding syntax in word representation; 2019 A structural probe for finding syntax in word representation; 2006 Reducing the dimensionality of data with neural networks |
| `general` | ngram | 4 | 0.29 | A,B | 5 (1) | 2001 Topographic independent component analysis; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2013 Auto-Encoding Variational Bayes |
| `high` | ngram | 4 | 0.41 | A,B | 6 (1) | 2002 The cognitive neuroscience of confabulation - A review and a; 2001 Topographic independent component analysis; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `abundancy` | ngram | 3 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `xenograft` | ngram | 3 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `valine abundancy` | ngram | 3 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `a valine` | ngram | 3 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `valine sensor` | ngram | 3 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `directly binding` | ngram | 3 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `a valine sensor` | ngram | 3 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `by directly binding` | ngram | 3 | 0.00 | ? | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `by directly` | ngram | 3 | 0.00 | A,G | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `binding` | ngram | 3 | 0.02 | A,E | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `levels` | ngram | 3 | 0.07 | A,B | 1 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `sensor` | ngram | 3 | 0.13 | A,G | 2 (1) | 2025 Human HDAC6 senses valine abundancy to regulate DNA damage; 2019 Large-scale assessment of a smartwatch to identify atrial fi |
| `level` | ngram | 3 | 0.23 | A,B | 3 (1) | 2006 Reducing the dimensionality of data with neural networks; 2019 Neurocognitive Signatures of Naturalistic Reading of Scienti; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |
| `mechanism` | ngram | 3 | 0.23 | A,G | 2 (1) | 2006 Reducing the dimensionality of data with neural networks; 2025 Human HDAC6 senses valine abundancy to regulate DNA damage |

