"""
Semantic Sentence Similarity Checker with Storage
Extended version that maintains a list of stored subheadings for comparison
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class SemanticSimilarityChecker:
    """
    A class to check semantic similarity between sentences using sentence embeddings.
    Extended to store and compare against a list of previously seen subheadings.
    """
    
    def __init__(self, model_name='all-MiniLM-L6-v2', threshold=0.75):
        """
        Initialize the similarity checker with a pre-trained model.
        
        Args:
            model_name (str): Name of the sentence transformer model to use.
            threshold (float): Similarity threshold (0-1). Values above this are considered similar.
        """
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        self.stored_subheadings = []  # List to store unique subheadings
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
        Check if two sentences are semantically similar.
        
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
    
    def is_similar_to_any_stored(self, new_subheading):
        """
        Check if a new subheading is similar to any stored subheading.
        
        Args:
            new_subheading (str): The new subheading to check
            
        Returns:
            tuple: (bool, float, str) - (is_similar, max_similarity_score, most_similar_subheading)
                   Returns (False, 0.0, None) if no stored subheadings exist
        """
        if not self.stored_subheadings:
            return False, 0.0, None
        
        max_similarity = 0.0
        most_similar = None
        
        for stored_subheading in self.stored_subheadings:
            similarity = self.calculate_similarity(new_subheading, stored_subheading)
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar = stored_subheading
        
        is_similar = max_similarity >= self.threshold
        return is_similar, max_similarity, most_similar
    
    def add_subheading(self, subheading):
        """
        Add a new unique subheading to the stored list.
        
        Args:
            subheading (str): The subheading to add
            
        Returns:
            bool: True if added successfully, False if it's similar to existing ones
        """
        is_similar, score, similar_to = self.is_similar_to_any_stored(subheading)
        
        if is_similar:
            print(f"⚠️  Subheading not added (too similar to: '{similar_to}' with score {score:.3f})")
            return False
        
        self.stored_subheadings.append(subheading)
        print(f"✅ Added subheading: '{subheading}' (Total: {len(self.stored_subheadings)})")
        return True
    
    def get_stored_subheadings(self):
        """
        Get the list of all stored subheadings.
        
        Returns:
            list: List of stored subheadings
        """
        return self.stored_subheadings.copy()
    
    def clear_stored_subheadings(self):
        """
        Clear all stored subheadings.
        """
        self.stored_subheadings = []
        print("🗑️  Cleared all stored subheadings")
    
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


# Example usage
if __name__ == "__main__":
    checker = SemanticSimilarityChecker(threshold=0.75)
    
    print("\n" + "="*70)
    print("TESTING SUBHEADING STORAGE AND SIMILARITY CHECKING")
    print("="*70 + "\n")
    
    # Simulate adding subheadings
    test_subheadings = [
        "Foundational Knowledge of Machine Learning",
        "Types of Machine Learning Algorithms",
        "Basic Concepts in ML",  # Similar to first one
        "Neural Networks and Deep Learning",
        "Understanding ML Fundamentals",  # Similar to first one
        "Supervised vs Unsupervised Learning",
        "Machine Learning Applications in Industry"
    ]
    
    for subheading in test_subheadings:
        print(f"\nAttempting to add: '{subheading}'")
        is_similar, score, similar_to = checker.is_similar_to_any_stored(subheading)
        
        if is_similar:
            print(f"  ❌ REJECTED - Similar to '{similar_to}' (score: {score:.3f})")
        else:
            checker.add_subheading(subheading)
    
    print("\n" + "="*70)
    print("FINAL STORED SUBHEADINGS:")
    print("="*70)
    for i, subheading in enumerate(checker.get_stored_subheadings(), 1):
        print(f"{i}. {subheading}")
