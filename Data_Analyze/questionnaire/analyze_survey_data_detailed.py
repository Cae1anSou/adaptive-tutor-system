import json
import numpy as np
from scipy import stats

def load_data(file_path):
    """Load the processed survey data"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_sus_score(sus_responses):
    """Calculate SUS score according to the standard algorithm"""
    # SUS scoring algorithm:
    # - Odd numbered items (1,3,5,7,9): score = value - 1
    # - Even numbered items (2,4,6,8,10): score = 5 - value
    # - Total score = sum of all scores * 2.5 (to convert to 0-100 scale)
    
    scores = []
    for i, response in enumerate(sus_responses):
        if i % 2 == 0:  # Odd items (0-indexed: 0,2,4,6,8)
            scores.append(response - 1)
        else:  # Even items (0-indexed: 1,3,5,7,9)
            scores.append(5 - response)
    
    total_score = sum(scores)
    scaled_score = total_score * 2.5  # Convert to 0-100 scale
    return scaled_score

def calculate_nasa_tlx_unweighted(nasa_responses):
    """Calculate NASA-TLX score (simple average of 6 dimensions)"""
    # Each dimension is already on 1-20 scale (but our data is 1-9, so we'll use as is)
    # For analysis, we can use the raw average
    return np.mean(nasa_responses)

def calculate_nasa_tlx_weighted(nasa_responses, weights=None):
    """Calculate weighted NASA-TLX score"""
    # If no weights provided, use equal weights (simple average)
    if weights is None:
        weights = [1/6] * 6  # Equal weights
    
    # Calculate weighted score
    weighted_score = sum(score * weight for score, weight in zip(nasa_responses, weights))
    return weighted_score

def apply_custom_weights(data, weights_dict=None):
    """Apply custom weights to NASA-TLX scores for each participant"""
    if weights_dict is None:
        # Use equal weights for all participants if no custom weights provided
        weights_dict = {pid: [1/6] * 6 for pid in data.keys()}
    
    # Apply weights to each participant
    weighted_data = {}
    for participant_id, scores in data.items():
        if participant_id in weights_dict:
            custom_weights = weights_dict[participant_id]
        else:
            # Use equal weights if participant not in weights_dict
            custom_weights = [1/6] * 6
        
        # Calculate weighted NASA-TLX score
        weighted_nasa = calculate_nasa_tlx_weighted(scores['NASA-TLX'], custom_weights)
        
        # Store results
        weighted_data[participant_id] = {
            'original_scores': scores,
            'weights': custom_weights,
            'weighted_nasa_score': weighted_nasa
        }
    
    return weighted_data

# def calculate_cpes_score(cpes_responses):
#     """Calculate CPES score (average of 12 items) - DEPRECATED"""
#     # Each item is on 1-5 scale
#     return np.mean(cpes_responses)

def analyze_groups(data):
    """Analyze data by groups (exp vs baseline)"""
    group_a = {}  # exp group
    group_b = {}  # baseline group
    
    for participant_id, scores in data.items():
        if participant_id.startswith('exp'):
            group_a[participant_id] = scores
        elif participant_id.startswith('baseline'):
            group_b[participant_id] = scores
    
    return group_a, group_b

def compute_group_statistics(group_data):
    """Compute statistics for a group"""
    sus_scores = []
    nasa_unweighted_scores = []
    nasa_weighted_scores = []
    
    # For demonstration, we'll use equal weights for all participants
    # In a real NASA-TLX study, participants would rate the importance of each dimension
    weights = [1/6] * 6  # Equal weights for all dimensions
    
    for participant_id, scores in group_data.items():
        sus_score = calculate_sus_score(scores['SUS'])
        nasa_unweighted_score = calculate_nasa_tlx_unweighted(scores['NASA-TLX'])
        nasa_weighted_score = calculate_nasa_tlx_weighted(scores['NASA-TLX'], weights)
        
        sus_scores.append(sus_score)
        nasa_unweighted_scores.append(nasa_unweighted_score)
        nasa_weighted_scores.append(nasa_weighted_score)
    
    return {
        'sus': {
            'scores': sus_scores,
            'mean': np.mean(sus_scores),
            'std': np.std(sus_scores)
        },
        'nasa_unweighted': {
            'scores': nasa_unweighted_scores,
            'mean': np.mean(nasa_unweighted_scores),
            'std': np.std(nasa_unweighted_scores)
        },
        'nasa_weighted': {
            'scores': nasa_weighted_scores,
            'mean': np.mean(nasa_weighted_scores),
            'std': np.std(nasa_weighted_scores)
        }
    }

def perform_statistical_tests(group_a_stats, group_b_stats):
    """Perform t-tests between groups"""
    results = {}
    
    # SUS tests
    # t-test
    t_stat, p_val = stats.ttest_ind(group_a_stats['sus']['scores'], 
                                    group_b_stats['sus']['scores'])
    results['sus'] = {
        't_test': {'statistic': t_stat, 'p_value': p_val}
    }
    
    # NASA-TLX unweighted tests
    # t-test
    t_stat, p_val = stats.ttest_ind(group_a_stats['nasa_unweighted']['scores'], 
                                    group_b_stats['nasa_unweighted']['scores'])
    results['nasa_unweighted'] = {
        't_test': {'statistic': t_stat, 'p_value': p_val}
    }
    
    # NASA-TLX weighted tests
    # t-test
    t_stat, p_val = stats.ttest_ind(group_a_stats['nasa_weighted']['scores'], 
                                    group_b_stats['nasa_weighted']['scores'])
    results['nasa_weighted'] = {
        't_test': {'statistic': t_stat, 'p_value': p_val}
    }
    
    
    return results

def analyze_nasa_dimensions(data):
    """Analyze each NASA-TLX dimension separately"""
    # NASA-TLX dimensions in order:
    # 1. Mental Demand
    # 2. Physical Demand
    # 3. Temporal Demand
    # 4. Performance
    # 5. Effort
    # 6. Frustration
    
    dimension_names = [
        "Mental Demand",
        "Physical Demand", 
        "Temporal Demand",
        "Performance",
        "Effort",
        "Frustration"
    ]
    
    # Separate groups
    group_a, group_b = analyze_groups(data)
    
    # Collect data for each dimension
    group_a_dimensions = {name: [] for name in dimension_names}
    group_b_dimensions = {name: [] for name in dimension_names}
    
    # Process Group A
    for participant_id, scores in group_a.items():
        nasa_scores = scores['NASA-TLX']
        for i, score in enumerate(nasa_scores):
            group_a_dimensions[dimension_names[i]].append(score)
    
    # Process Group B
    for participant_id, scores in group_b.items():
        nasa_scores = scores['NASA-TLX']
        for i, score in enumerate(nasa_scores):
            group_b_dimensions[dimension_names[i]].append(score)
    
    # Calculate statistics for each dimension
    dimension_stats = {}
    for i, name in enumerate(dimension_names):
        group_a_mean = np.mean(group_a_dimensions[name])
        group_a_std = np.std(group_a_dimensions[name])
        group_b_mean = np.mean(group_b_dimensions[name])
        group_b_std = np.std(group_b_dimensions[name])
        
        # T-test for this dimension
        t_stat, p_val = stats.ttest_ind(group_a_dimensions[name], group_b_dimensions[name])
        
        dimension_stats[name] = {
            'group_a_mean': group_a_mean,
            'group_a_std': group_a_std,
            'group_b_mean': group_b_mean,
            'group_b_std': group_b_std,
            't_statistic': t_stat,
            'p_value': p_val
        }
    
    return dimension_stats

def main():
    # Load data
    data = load_data('Data_Analyze/questionnaire/processed_survey_data.json')
    
    # Prepare output strings
    output_lines = []
    
    # Separate groups
    group_a, group_b = analyze_groups(data)
    
    output_lines.append(f"Group A (exp): {len(group_a)} participants")
    output_lines.append(f"Group B (baseline): {len(group_b)} participants")
    
    # Compute statistics for each group
    group_a_stats = compute_group_statistics(group_a)
    group_b_stats = compute_group_statistics(group_b)
    
    # Print descriptive statistics
    output_lines.append("\n=== DESCRIPTIVE STATISTICS ===")
    output_lines.append("\nGroup A (exp) - Mean (SD):")
    output_lines.append(f"SUS: {group_a_stats['sus']['mean']:.2f} ({group_a_stats['sus']['std']:.2f})")
    output_lines.append(f"NASA-TLX (Unweighted): {group_a_stats['nasa_unweighted']['mean']:.2f} ({group_a_stats['nasa_unweighted']['std']:.2f})")
    # output_lines.append(f"NASA-TLX (Weighted): {group_a_stats['nasa_weighted']['mean']:.2f} ({group_a_stats['nasa_weighted']['std']:.2f})")
    # output_lines.append(f"CPES: {group_a_stats['cpes']['mean']:.2f} ({group_a_stats['cpes']['std']:.2f})")
    
    output_lines.append("\nGroup B (baseline) - Mean (SD):")
    output_lines.append(f"SUS: {group_b_stats['sus']['mean']:.2f} ({group_b_stats['sus']['std']:.2f})")
    output_lines.append(f"NASA-TLX (Unweighted): {group_b_stats['nasa_unweighted']['mean']:.2f} ({group_b_stats['nasa_unweighted']['std']:.2f})")
    # output_lines.append(f"NASA-TLX (Weighted): {group_b_stats['nasa_weighted']['mean']:.2f} ({group_b_stats['nasa_weighted']['std']:.2f})")
    # output_lines.append(f"CPES: {group_b_stats['cpes']['mean']:.2f} ({group_b_stats['cpes']['std']:.2f})")
    
    # Perform statistical tests
    test_results = perform_statistical_tests(group_a_stats, group_b_stats)
    
    output_lines.append("\n=== STATISTICAL TESTS ===")
    output_lines.append("\n--- t-tests ---")
    output_lines.append(f"SUS - t({len(group_a_stats['sus']['scores']) + len(group_b_stats['sus']['scores']) - 2}) = {test_results['sus']['t_test']['statistic']:.3f}, p = {test_results['sus']['t_test']['p_value']:.3f}")
    output_lines.append(f"NASA-TLX (Unweighted) - t({len(group_a_stats['nasa_unweighted']['scores']) + len(group_b_stats['nasa_unweighted']['scores']) - 2}) = {test_results['nasa_unweighted']['t_test']['statistic']:.3f}, p = {test_results['nasa_unweighted']['t_test']['p_value']:.3f}")
    # output_lines.append(f"NASA-TLX (Weighted) - t({len(group_a_stats['nasa_weighted']['scores']) + len(group_b_stats['nasa_weighted']['scores']) - 2}) = {test_results['nasa_weighted']['t_test']['statistic']:.3f}, p = {test_results['nasa_weighted']['t_test']['p_value']:.3f}")
    # output_lines.append(f"CPES - t({len(group_a_stats['cpes']['scores']) + len(group_b_stats['cpes']['scores']) - 2}) = {test_results['cpes']['t_test']['statistic']:.3f}, p = {test_results['cpes']['t_test']['p_value']:.3f}")
    
    
    # Effect sizes (Cohen's d)
    def cohens_d(group1, group2):
        """Calculate Cohen's d effect size"""
        diff = np.mean(group1) - np.mean(group2)
        pooled_std = np.sqrt(((len(group1) - 1) * np.var(group1) + (len(group2) - 1) * np.var(group2)) / (len(group1) + len(group2) - 2))
        return diff / pooled_std
    
    output_lines.append("\n=== EFFECT SIZES (Cohen's d) ===")
    sus_d = cohens_d(group_a_stats['sus']['scores'], group_b_stats['sus']['scores'])
    nasa_unweighted_d = cohens_d(group_a_stats['nasa_unweighted']['scores'], group_b_stats['nasa_unweighted']['scores'])
    # nasa_weighted_d = cohens_d(group_a_stats['nasa_weighted']['scores'], group_b_stats['nasa_weighted']['scores'])
    # cpes_d = cohens_d(group_a_stats['cpes']['scores'], group_b_stats['cpes']['scores'])
    
    output_lines.append(f"SUS: d = {sus_d:.3f}")
    output_lines.append(f"NASA-TLX (Unweighted): d = {nasa_unweighted_d:.3f}")
    # output_lines.append(f"NASA-TLX (Weighted): d = {nasa_weighted_d:.3f}")
    # output_lines.append(f"CPES: d = {cpes_d:.3f}")
    
    # Analyze individual NASA-TLX dimensions
    output_lines.append("\n=== INDIVIDUAL NASA-TLX DIMENSIONS ANALYSIS ===")
    dimension_stats = analyze_nasa_dimensions(data)
    
    for dimension, stats in dimension_stats.items():
        output_lines.append(f"\n{dimension}:")
        output_lines.append(f"  Group A: {stats['group_a_mean']:.2f} ({stats['group_a_std']:.2f})")
        output_lines.append(f"  Group B: {stats['group_b_mean']:.2f} ({stats['group_b_std']:.2f})")
        output_lines.append(f"  t({len(group_a) + len(group_b) - 2}) = {stats['t_statistic']:.3f}, p = {stats['p_value']:.3f}")
    
    # Print to console
    for line in output_lines:
        print(line)
    
    # Save to file
    with open('Data_Analyze/questionnaire/analysis_results.txt', 'w', encoding='utf-8') as f:
        for line in output_lines:
            f.write(line + '\n')
    
    print("\nAnalysis results have been saved to Data_Analyze/questionnaire/analysis_results.txt")

if __name__ == "__main__":
    main()