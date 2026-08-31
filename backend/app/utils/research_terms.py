"""
Curated keyword lists used for rule-based extraction of research-specific
entities that generic NER models (PERSON/ORG/etc.) don't reliably capture.

These lists are intentionally hand-curated rather than derived from generic
NER labels, since off-the-shelf NER does not have MODEL/DATASET/METRIC
categories and would otherwise mislabel these as ORG or MISC.

Matching is case-insensitive and phrase-based (via spaCy's PhraseMatcher),
so multi-word entries like "Random Forest" are matched as whole phrases.
"""

MODELS = [
    "BERT", "RoBERTa", "ALBERT", "DistilBERT", "ELECTRA", "XLNet", "ELMo",
    "GPT", "GPT-2", "GPT-3", "GPT-4", "T5", "BART", "LLaMA", "PaLM",
    "ResNet", "VGG", "AlexNet", "GoogLeNet", "Inception", "EfficientNet",
    "MobileNet", "DenseNet", "U-Net", "YOLO", "Faster R-CNN", "Mask R-CNN",
    "ViT", "Vision Transformer",
    "LSTM", "GRU", "RNN", "CNN", "Transformer", "Bidirectional GRU",
    "Bidirectional LSTM", "Seq2Seq", "Autoencoder", "GAN",
    "Word2Vec", "GloVe", "FastText",
    "XGBoost", "LightGBM", "CatBoost", "Random Forest", "SVM",
    "Support Vector Machine", "Naive Bayes", "Logistic Regression",
    "Decision Tree", "K-Means", "K-Nearest Neighbors", "KNN",
]

DATASETS = [
    "ImageNet", "COCO", "MNIST", "Fashion-MNIST", "CIFAR-10", "CIFAR-100",
    "SQuAD", "GLUE", "SuperGLUE", "WikiText", "IMDB", "SST-2", "CoNLL",
    "PASCAL VOC", "Penn Treebank", "Common Crawl", "WMT", "MS MARCO",
    "Kaggle", "UCI", "Reuters", "20 Newsgroups", "Yelp", "Amazon Reviews",
    "OpenWebText", "BookCorpus", "LibriSpeech", "VQA", "Visual Genome",
]

METRICS = [
    "Accuracy", "Precision", "Recall", "F1-score", "F1 score", "F1",
    "AUC", "ROC", "ROC-AUC", "BLEU", "ROUGE", "METEOR", "Perplexity",
    "MSE", "RMSE", "MAE", "R2", "mAP", "IoU", "Top-1 accuracy",
    "Top-5 accuracy", "Exact Match", "WER", "Word Error Rate",
    "Confusion Matrix", "Log Loss",
]

METHODS_ALGORITHMS = [
    "Fine-tuning", "Transfer Learning", "Backpropagation", "Gradient Descent",
    "Stochastic Gradient Descent", "Attention Mechanism", "Self-Attention",
    "Cross-Validation", "Data Augmentation", "Dropout", "Batch Normalization",
    "Regularization", "Ensemble Learning", "Reinforcement Learning",
    "Supervised Learning", "Unsupervised Learning", "Semi-Supervised Learning",
    "Active Learning", "Hyperparameter Tuning", "Grid Search",
    "Class Weighting", "Early Stopping",
]

TECHNOLOGIES = [
    "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Hugging Face",
    "spaCy", "NLTK", "OpenCV", "Pandas", "NumPy", "CUDA", "GPU", "TPU",
    "Docker", "FastAPI", "Flask", "FAISS", "Elasticsearch",
]

ALL_CATEGORIES = {
    "models": MODELS,
    "datasets": DATASETS,
    "metrics": METRICS,
    "methods": METHODS_ALGORITHMS,
    "technologies": TECHNOLOGIES,
}
