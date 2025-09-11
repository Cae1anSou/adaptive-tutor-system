import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Set style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("Set2")

def load_data(file_path):
    """Load the processed survey data"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_sus_score(sus_responses):
    """Calculate SUS score according to the standard algorithm"""
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
    return np.mean(nasa_responses)

def prepare_data_for_boxplot(data):
    """Prepare data for boxplot visualization"""
    group_a_sus = []
    group_b_sus = []
    group_a_nasa = []
    group_b_nasa = []
    
    # NASA-TLX dimensions
    nasa_dimensions = ["Mental", "Physical", "Temporal", "Performance", "Effort", "Frustration"]
    group_a_dimensions = {dim: [] for dim in nasa_dimensions}
    group_b_dimensions = {dim: [] for dim in nasa_dimensions}
    
    for participant_id, scores in data.items():
        sus_score = calculate_sus_score(scores['SUS'])
        nasa_score = calculate_nasa_tlx_unweighted(scores['NASA-TLX'])
        
        if participant_id.startswith('exp'):
            group_a_sus.append(sus_score)
            group_a_nasa.append(nasa_score)
            # Add NASA-TLX dimensions
            for i, dim in enumerate(nasa_dimensions):
                group_a_dimensions[dim].append(scores['NASA-TLX'][i])
        elif participant_id.startswith('baseline'):
            group_b_sus.append(sus_score)
            group_b_nasa.append(nasa_score)
            # Add NASA-TLX dimensions
            for i, dim in enumerate(nasa_dimensions):
                group_b_dimensions[dim].append(scores['NASA-TLX'][i])
    
    return {
        'sus': {'group_a': group_a_sus, 'group_b': group_b_sus},
        'nasa': {'group_a': group_a_nasa, 'group_b': group_b_nasa},
        'nasa_dimensions': {
            'group_a': group_a_dimensions,
            'group_b': group_b_dimensions
        }
    }

def create_boxplot(data_dict):
    """Create boxplot for SUS and NASA-TLX scores"""
    # Prepare data for boxplot
    sus_data = [data_dict['sus']['group_a'], data_dict['sus']['group_b']]
    nasa_data = [data_dict['nasa']['group_a'], data_dict['nasa']['group_b']]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # SUS Boxplot
    box1 = ax1.boxplot(sus_data, labels=['Experiment Group', 'Baseline Group'], patch_artist=True)
    box1['boxes'][0].set_facecolor('blue')      # Experiment group - Blue
    box1['boxes'][1].set_facecolor('orange')    # Baseline group - Orange
    box1['medians'][0].set_color('white')
    box1['medians'][1].set_color('white')
    ax1.set_title('System Usability Scale (SUS)', fontsize=22)
    ax1.set_ylabel('SUS Score', fontsize=18)
    ax1.set_xlabel('Group', fontsize=18)
    ax1.tick_params(axis='both', which='major', labelsize=18)
    ax1.grid(True, alpha=0.3)
    
    # NASA-TLX Boxplot
    box2 = ax2.boxplot(nasa_data, labels=['Experiment Group', 'Baseline Group'], patch_artist=True)
    box2['boxes'][0].set_facecolor('blue')      # Experiment group - Blue
    box2['boxes'][1].set_facecolor('orange')    # Baseline group - Orange
    box2['medians'][0].set_color('white')
    box2['medians'][1].set_color('white')
    ax2.set_title('NASA Task Load Index (NASA-TLX)', fontsize=22)
    ax2.set_ylabel('NASA-TLX Score', fontsize=18)
    ax2.set_xlabel('Group', fontsize=18)
    ax2.tick_params(axis='both', which='major', labelsize=18)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('Data_Analyze/questionnaire/sus_nasa_boxplot.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_radar_chart(data_dict):
    """Create radar chart for NASA-TLX dimensions"""
    # Calculate mean values for each dimension
    nasa_dimensions = ["Mental", "Physical", "Temporal", "Performance", "Effort", "Frustration"]
    
    group_a_means = [np.mean(data_dict['nasa_dimensions']['group_a'][dim]) for dim in nasa_dimensions]
    group_b_means = [np.mean(data_dict['nasa_dimensions']['group_b'][dim]) for dim in nasa_dimensions]
    
    # Create radar chart
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    # Number of variables
    N = len(nasa_dimensions)
    
    # What angles are needed?
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Repeat first value to close the circle
    
    # Add data
    group_a_data = group_a_means + [group_a_means[0]]
    group_b_data = group_b_means + [group_b_means[0]]
    
    # Plot data
    ax.plot(angles, group_a_data, linewidth=2, linestyle='solid', label='Experiment Group', color='blue')
    ax.fill(angles, group_a_data, alpha=0.25, color='blue')
    
    ax.plot(angles, group_b_data, linewidth=2, linestyle='solid', label='Baseline Group', color='orange')
    ax.fill(angles, group_b_data, alpha=0.25, color='orange')
    
    # Add labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(nasa_dimensions, fontsize=18)
    ax.tick_params(axis='y', which='major', labelsize=18)
    
    # Add title and legend
    ax.set_title('NASA Task Load Index Dimensions Comparison', size=22, pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.5, 1.0), fontsize=18)
    
    # Set y-labels
    ax.set_ylim(0, 10)
    
    plt.tight_layout()
    plt.savefig('Data_Analyze/questionnaire/nasa_radar_chart.png', dpi=300, bbox_inches='tight')
    plt.show()

def main():
    # Load data
    data = load_data('Data_Analyze/questionnaire/processed_survey_data.json')
    
    # Prepare data for visualization
    data_dict = prepare_data_for_boxplot(data)
    
    # Create boxplot
    create_boxplot(data_dict)
    
    # Create radar chart
    create_radar_chart(data_dict)
    
    print("Visualizations have been created and saved:")
    print("- Data_Analyze/questionnaire/sus_nasa_boxplot.png")
    print("- Data_Analyze/questionnaire/nasa_radar_chart.png")

if __name__ == "__main__":
    main()