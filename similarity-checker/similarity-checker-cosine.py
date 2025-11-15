"""
Semantic Sentence Similarity Checker using Sentence Transformers
This implementation uses cosine similarity with sentence embeddings to determine
if two sentences have similar meanings, even if they use different words.
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class SemanticSimilarityChecker:
    """
    A class to check semantic similarity between sentences using sentence embeddings.
    """
    
    def __init__(self, model_name='all-MiniLM-L6-v2', threshold=0.75):
        """
        Initialize the similarity checker with a pre-trained model.
        
        Args:
            model_name (str): Name of the sentence transformer model to use.
                             'all-MiniLM-L6-v2' is fast and accurate (default)
                             'all-mpnet-base-v2' is more accurate but slower
                             'paraphrase-multilingual-MiniLM-L12-v2' for multilingual support
            threshold (float): Similarity threshold (0-1). Values above this are considered similar.
                              Default is 0.75 (75% similarity)
        """
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        print(f"Loaded model: {model_name}")
        print(f"Similarity threshold: {threshold}")
    
    def get_embeddings(self, sentences):
        """
        Convert sentences to embeddings (vector representations).
        
        Args:
            sentences (list or str): Single sentence or list of sentences
            
        Returns:
            numpy.ndarray: Embeddings for the input sentences
        """
        if isinstance(sentences, str):
            sentences = [sentences]
        return self.model.encode(sentences)
    
    def calculate_similarity(self, sentence1, sentence2):
        """
        Calculate cosine similarity between two sentences.
        
        Args:
            sentence1 (str): First sentence
            sentence2 (str): Second sentence
            
        Returns:
            float: Similarity score between 0 and 1 (1 being most similar)
        """
        embeddings = self.get_embeddings([sentence1, sentence2])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return float(similarity)
    
    def are_similar(self, sentence1, sentence2, return_score=False):
        """
        Main function: Check if two sentences are semantically similar.
        
        Args:
            sentence1 (str): First sentence
            sentence2 (str): Second sentence
            return_score (bool): If True, return both result and similarity score
            
        Returns:
            bool or tuple: True if similar, False otherwise
                          If return_score=True, returns (bool, float) tuple
        """
        similarity_score = self.calculate_similarity(sentence1, sentence2)
        is_similar = similarity_score >= self.threshold
        
        if return_score:
            return is_similar, similarity_score
        return is_similar
    
    def batch_compare(self, sentence, sentence_list):
        """
        Compare one sentence against multiple sentences.
        
        Args:
            sentence (str): The reference sentence
            sentence_list (list): List of sentences to compare against
            
        Returns:
            list: List of tuples (similarity_score, is_similar) for each comparison
        """
        results = []
        for s in sentence_list:
            similarity = self.calculate_similarity(sentence, s)
            results.append((similarity, similarity >= self.threshold))
        return results


# Simple wrapper function for quick usage
def check_similarity(sentence1, sentence2, threshold=0.75):
    """
    Blackbox function to check if two sentences are similar.
    
    Args:
        sentence1 (str): First sentence
        sentence2 (str): Second sentence
        threshold (float): Similarity threshold (default 0.75)
        
    Returns:
        bool: True if sentences are similar, False otherwise
    """
    checker = SemanticSimilarityChecker(threshold=threshold)
    return checker.are_similar(sentence1, sentence2)


# Example usage and testing
if __name__ == "__main__":
    # Initialize the checker
    checker = SemanticSimilarityChecker(threshold=0.75)
    
    print("\n" + "="*70)
    print("SEMANTIC SIMILARITY CHECKER - DEMO")
    print("="*70)
    
    # Test cases demonstrating semantic understanding
    test_pairs = [
        ("The cat sat on the mat", "A feline rested on the rug"),
        ("I love programming", "I enjoy coding"),
        ("The weather is beautiful today", "It's a gorgeous day outside"),
        ("Python is a programming language", "Paris is the capital of France"),
        ("He is eating an apple", "She is consuming fruit"),
        ("The movie was terrible", "The film was excellent"),
        ("I need to buy groceries", "I have to purchase food items"),
        ("The car is red", "The sky is blue"),
        ("Dijkstra's algorithm finds the shortest path between nodes in a graph with non-negative edge weights", "The shortest path algorithm requires edge weights to be positive or zero for correctness.")
    ]
    
    print("\nTesting sentence pairs:\n")
    for s1, s2 in test_pairs:
        is_similar, score = checker.are_similar(s1, s2, return_score=True)
        status = "✓ SIMILAR" if is_similar else "✗ NOT SIMILAR"
        print(f"{status} (score: {score:.3f})")
        print(f"  Sentence 1: '{s1}'")
        print(f"  Sentence 2: '{s2}'")
        print()
    
    print("="*70)
    print("\nUsing the blackbox function:")
    result = check_similarity(
        "The dog is playing in the garden",
        "A canine is having fun in the yard"
    )
    print(f"Are the sentences similar? {result}")
    
    print("\n" + "="*70)
    print("BATCH COMPARISON EXAMPLE")
    print("="*70)
    
    reference = "I want to learn machine learning"
    candidates = [
        "I'm interested in studying AI",
        "I need to buy a new car",
        "Machine learning is something I'd like to understand",
        "What time is it?"
    ]
    
    print(f"\nReference: '{reference}'\n")
    results = checker.batch_compare(reference, candidates)
    
    for i, (candidate, (score, is_similar)) in enumerate(zip(candidates, results), 1):
        status = "✓" if is_similar else "✗"
        print(f"{status} [{score:.3f}] {candidate}")