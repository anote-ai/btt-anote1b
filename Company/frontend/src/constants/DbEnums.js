export const AccessLevel = {
	ADMIN: 0,
	ANNOTATOR: 1
};

export const NLPTask = {
    TEXT_CLASSIFICATION: 0,
    NAMED_ENTITY_RECOGNITION: 1,
    PROMPTING: 2,
    CHATBOT: 3,
    // UNSUPERVISED: 4,
};

export const Decomposer = {
	STANDARD: 0,
	DOCUMENT: 1
};

export const NLPTaskFileName = {
    [NLPTask.TEXT_CLASSIFICATION]: 'TEXT_CLASSIFICATION',
    [NLPTask.NAMED_ENTITY_RECOGNITION]: 'NAMED_ENTITY_RECOGNITION',
    [NLPTask.PROMPTING]: 'PROMPTING',
    [NLPTask.CHATBOT]: 'CHATBOT',
    // [NLPTask.UNSUPERVISED]: 'UNSUPERVISED',
};

export const NLPTaskMap = {
    [NLPTask.TEXT_CLASSIFICATION]: 'Classify Text',
    [NLPTask.NAMED_ENTITY_RECOGNITION]: 'Extract Entities',
    [NLPTask.PROMPTING]: 'Answer Questions',
    [NLPTask.CHATBOT]: 'Chat with Docs',
    // [NLPTask.UNSUPERVISED]: 'Unsupervised Learning',
};

export const DecomposerMap = {
    [Decomposer['STANDARD']]: 'Per Line',
    [Decomposer['DOCUMENT']]: 'Per Document',
};

export const StructuredMap = {
    0: 'No',
    1: 'Yes',
};

export const ModelType = {
    NO_LABEL_TEXT_CLASSIFICATION: 0,
    FEW_SHOT_TEXT_CLASSIFICATION: 1,
    NAIVE_BAYES_TEXT_CLASSIFICATION: 2,
    SETFIT_TEXT_CLASSIFICATION: 3,
    NOT_ALL_TEXT_CLASSIFICATION: 4,
    FEW_SHOT_NAMED_ENTITY_RECOGNITION: 5,
    EXAMPLE_BASED_NAMED_ENTITY_RECOGNITION: 6,
    GPT_FOR_PROMPTING: 7,
    PROMPT_NAMED_ENTITY_RECOGNITION: 8,
    PROMPTING_WITH_FEEDBACK_PROMPT_ENGINEERED: 9,
    DUMMY: 10,
    GPT_FINETUNING: 11,
    RAG_UNSUPERVISED: 12,
    ZEROSHOT_GPT4: 13,
    // ZEROSHOT_CLAUDE: 14,
    // ZEROSHOT_LLAMA3: 15,
    // ZEROSHOT_MISTRAL: 16,
    // ZEROSHOT_GPT4MINI: 17,
    // ZEROSHOT_GEMINI: 18
};

export const ModelTypeNames = {
    [ModelType.NO_LABEL_TEXT_CLASSIFICATION]: 'No Label Text Classification',
    [ModelType.FEW_SHOT_TEXT_CLASSIFICATION]: 'Few Shot Text Classification',
    [ModelType.NAIVE_BAYES_TEXT_CLASSIFICATION]: 'Naive Bayes Text Classification',
    [ModelType.SETFIT_TEXT_CLASSIFICATION]: 'SetFit Text Classification',
    [ModelType.NOT_ALL_TEXT_CLASSIFICATION]: 'Not All Text Classification',
    [ModelType.FEW_SHOT_NAMED_ENTITY_RECOGNITION]: 'Few Shot Named Entity Recognition',
    [ModelType.EXAMPLE_BASED_NAMED_ENTITY_RECOGNITION]: 'Example Based Named Entity Recognition',
    [ModelType.GPT_FOR_PROMPTING]: 'GPT for Prompting',
    [ModelType.PROMPT_NAMED_ENTITY_RECOGNITION]: 'Prompt Named Entity Recognition',
    [ModelType.PROMPTING_WITH_FEEDBACK_PROMPT_ENGINEERED]: 'Prompting with Feedback Prompt Engineered',
    [ModelType.DUMMY]: 'Dummy',
    [ModelType.GPT_FINETUNING]: 'GPT Finetuning',
    [ModelType.RAG_UNSUPERVISED]: 'RAG Unsupervised',
    [ModelType.ZEROSHOT_GPT4]: 'Anote Model',
    // [ModelType.ZEROSHOT_CLAUDE]: 'Zero Shot Claude',
    // [ModelType.ZEROSHOT_LLAMA3]: 'Zero Shot Llama-3',
    // [ModelType.ZEROSHOT_MISTRAL]: 'Zero Shot Mistral',
    // [ModelType.ZEROSHOT_GPT4MINI]: 'Zero Shot GPT-4 Mini',
    // [ModelType.ZEROSHOT_GEMINI]: 'Zero Shot Gemini'
  };

export const ZeroShotModelType = {
    // ZERO_SHOT_GPT4: ModelType.PROMPTING_WITH_FEEDBACK_PROMPT_ENGINEERED,
    ZERO_SHOT_GPT4: ModelType.ZEROSHOT_GPT4,
    // ZERO_SHOT_CLAUDE: ModelType.ZEROSHOT_CLAUDE,
    // ZERO_SHOT_LLAMA3: ModelType.ZEROSHOT_LLAMA3,
    // ZERO_SHOT_MISTRAL: ModelType.ZEROSHOT_MISTRAL,
    // ZERO_SHOT_GPT4_MINI: ModelType.ZEROSHOT_GPT4MINI,
    // ZERO_SHOT_GEMINI: ModelType.ZEROSHOT_GEMINI,
};

export const ZeroShotModelNames = {
    [ZeroShotModelType.ZERO_SHOT_GPT4]: 'Anote Model',
    // [ZeroShotModelType.ZERO_SHOT_CLAUDE]: 'Claude',
    // [ZeroShotModelType.ZERO_SHOT_LLAMA3]: 'LLaMA-3',
    // [ZeroShotModelType.ZERO_SHOT_MISTRAL]: 'Mistral',
    // [ZeroShotModelType.ZERO_SHOT_GPT4_MINI]: 'GPT-4 Mini',
    // [ZeroShotModelType.ZERO_SHOT_GEMINI]: 'Gemini'
};

export const PaidUserStatus = {
    FREE_TIER: 0,
    BASIC_TIER: 1,
    STANDARD_TIER: 2,
    PREMIUM_TIER: 3,
    ENTERPRISE_TIER: 4
};

export const FlowType = {
    NONE: 0,
    LABEL: 1,
    TRAIN: 2,
    PREDICT: 3,
    EVALUATE: 4
};

export const FlowTypeFileName = {
    [FlowType.NONE]: 'NONE',
    [FlowType.LABEL]: 'LABEL',
    [FlowType.TRAIN]: 'TRAIN',
    [FlowType.PREDICT]: 'PREDICT',
    [FlowType.EVALUATE]: 'EVALUATE'
};

export const FlowPage = {
    // Shared pages that render different information based on FlowType
    DATA_SETTER: 0,
    CSV_SELECTOR: 1,
    CSV_VIEWER: 2,
    EVALUATE_DASHBOARD: 3,
    MODEL_TRAINING: 4,
    FINISH_TRAINING: 5,
    FLOW_OPTIONS: 6,
    CHATBOT: 7,
    SDK: 8,
    BENCHMARK_DATA_SELECTOR: 9,
    GENERATE_REPORTS: 10
};

export const EvaluationMetric = {
    COSINE_SIM: 0,
    BERT_SCORE: 1,
    ROUGE_L_F1: 2,
    FAITHFULNESS: 3,
    ANSWER_RELEVANCE: 4,
    ANOTE_MISLABEL_SCORE: 5,
    CONFUSION_MATRIX: 6,
    CLASSIFICATION_REPORT: 7,
    PRECISION: 8,
    RECALL: 9,
    F1: 10,
    IOU: 11,
    SUPPORT: 12
};

export const EvaluationMetricTypeNames = {
    [EvaluationMetric.COSINE_SIM]: "Cosine Similarity",
    [EvaluationMetric.BERT_SCORE]: "BERT Score",
    [EvaluationMetric.ROUGE_L_F1]: "ROUGE-L F1",
    [EvaluationMetric.FAITHFULNESS]: "Faithfulness",
    [EvaluationMetric.ANSWER_RELEVANCE]: "Answer Relevance",
    [EvaluationMetric.ANOTE_MISLABEL_SCORE]: "Annotation Mislabeled Score",
    [EvaluationMetric.CONFUSION_MATRIX]: "Confusion Matrix",
    [EvaluationMetric.CLASSIFICATION_REPORT]: "Classification Report",
    [EvaluationMetric.PRECISION]: "Precision",
    [EvaluationMetric.RECALL]: "Recall",
    [EvaluationMetric.F1]: "F1 Score",
    [EvaluationMetric.IOU]: "Intersection over Union (IoU)",
    [EvaluationMetric.SUPPORT]: "Support",
  };


// Mapping of NLP tasks to supported model types
export const SUPPORTED_MODEL_TYPE_FOR_TASK_TYPE_MAPPING = {
    "TEXT_CLASSIFICATION": [
        // ModelType.NO_LABEL_TEXT_CLASSIFICATION,
        // ModelType.FEW_SHOT_TEXT_CLASSIFICATION,
        ModelType.NAIVE_BAYES_TEXT_CLASSIFICATION
        // ModelType.SETFIT_TEXT_CLASSIFICATION,
        // ModelType.NOT_ALL_TEXT_CLASSIFICATION
    ],
    "NAMED_ENTITY_RECOGNITION": [
        // ModelType.FEW_SHOT_NAMED_ENTITY_RECOGNITION,
        // ModelType.EXAMPLE_BASED_NAMED_ENTITY_RECOGNITION,
        ModelType.PROMPT_NAMED_ENTITY_RECOGNITION
        //"PROMPT_NAMED_ENTITY_RECOGNITION"
    ],
    "PROMPTING": [
        // ModelType.GPT_FOR_PROMPTING,
        ModelType.PROMPTING_WITH_FEEDBACK_PROMPT_ENGINEERED
        // "PROMPTING_WITH_FEEDBACK_PROMPT_ENGINEERED"
    ],
    "CHATBOT": [
        // ModelType.GPT_FOR_PROMPTING,
        ModelType.PROMPTING_WITH_FEEDBACK_PROMPT_ENGINEERED
        // "PROMPTING_WITH_FEEDBACK_PROMPT_ENGINEERED"
    ],
    "UNSUPERVISED": [
        ModelType.RAG_UNSUPERVISED
    ]
};

// Mapping of NLP tasks to supported evaluation metrics
export const SUPPORTED_EVALUATION_METRIC_FOR_TASK_TYPE_MAPPING = {
    [NLPTask.TEXT_CLASSIFICATION]: [
        // EvaluationMetric.CONFUSION_MATRIX,
        // EvaluationMetric.CLASSIFICATION_REPORT,
        EvaluationMetric.PRECISION,
        EvaluationMetric.RECALL,
        EvaluationMetric.F1,
        EvaluationMetric.SUPPORT,
    ],
    [NLPTask.NAMED_ENTITY_RECOGNITION]: [
        // EvaluationMetric.PRECISION,
        // EvaluationMetric.RECALL,
        // EvaluationMetric.F1,
        EvaluationMetric.IOU
    ],
    [NLPTask.PROMPTING]: [
        EvaluationMetric.COSINE_SIM,
        // EvaluationMetric.BERT_SCORE,
        EvaluationMetric.ROUGE_L_F1,
        // EvaluationMetric.FAITHFULNESS,
        // EvaluationMetric.ANSWER_RELEVANCE,
        // EvaluationMetric.ANOTE_MISLABEL_SCORE
    ],
    [NLPTask.CHATBOT]: [
        EvaluationMetric.COSINE_SIM,
        // EvaluationMetric.BERT_SCORE,
        EvaluationMetric.ROUGE_L_F1,
        // EvaluationMetric.FAITHFULNESS,
        // EvaluationMetric.ANSWER_RELEVANCE,
        // EvaluationMetric.ANOTE_MISLABEL_SCORE
    ],
    [NLPTask.UNSUPERVISED]: [
        EvaluationMetric.COSINE_SIM,
        // EvaluationMetric.BERT_SCORE,
        EvaluationMetric.ROUGE_L_F1,
        // EvaluationMetric.FAITHFULNESS,
        // EvaluationMetric.ANSWER_RELEVANCE,
        // EvaluationMetric.ANOTE_MISLABEL_SCORE
    ],
};
