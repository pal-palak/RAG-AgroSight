import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import numpy as np
import networkx as nx

nltk.download('punkt')
nltk.download('stopwords')

def sentence_similarity(sent1, sent2, stopwords=None):
    if stopwords is None:
        stopwords = []

    words1 = [word.lower() for word in sent1 if word.isalnum()]
    words2 = [word.lower() for word in sent2 if word.isalnum()]

    if len(words1) == 0 or len(words2) == 0:
        return 0

    common_words = len(set(words1) & set(words2))
    return common_words / (np.log(len(words1)) + np.log(len(words2)))

def build_similarity_matrix(sentences, stopwords):
    similarity_matrix = np.zeros((len(sentences), len(sentences)))

    for i in range(len(sentences)):
        for j in range(len(sentences)):
            if i == j:
                continue
            similarity_matrix[i][j] = sentence_similarity(sentences[i], sentences[j], stopwords)

    return similarity_matrix

def textrank_summarize(text, num_sentences=3):
    sentences = sent_tokenize(text)
    stopwords = set(stopwords.words("english"))
    similarity_matrix = build_similarity_matrix(sentences, stopwords)
    scores = nx.pagerank(nx.from_numpy_array(similarity_matrix))

    ranked_sentences = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)

    summary = " ".join([sentence for score, sentence in ranked_sentences[:num_sentences]])
    return summary

# Example Usage
text = """
Text summarization is the process of distilling the most important information from a source to produce a shortened version for a particular audience or purpose.
The TextRank algorithm, inspired by Google's PageRank, assigns importance scores to sentences based on their similarity to other sentences in the text.
Extractive summarization methods select the most important sentences from the source text and concatenate them to form the summary.
One popular approach is the TextRank algorithm, which assigns importance scores to sentences based on their similarity to other sentences in the text.
"""

summary = textrank_summarize(text)
print("TextRank Summary:\n", summary)