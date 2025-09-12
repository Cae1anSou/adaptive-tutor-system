import json
import os
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Set style for better-looking plots
# plt.style.use('seaborn-v0_8')
# sns.set_palette("Set2")

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


def create_combined_figure(data_dict, save_path='Data_Analyze/questionnaire/combined_sus_nasa.png', dpi=300):
    """Create a single figure with three subplots:
       (a) SUS boxplot, (b) NASA-TLX boxplot, (c) NASA-TLX radar chart.
    """
    # ===== Prepare data =====
    sus_data  = [data_dict['sus']['group_a'],  data_dict['sus']['group_b']]
    nasa_data = [data_dict['nasa']['group_a'], data_dict['nasa']['group_b']]

    nasa_dimensions = ["Mental", "Physical", "Temporal", "Performance", "Effort", "Frustration"]
    group_a_means = [np.mean(data_dict['nasa_dimensions']['group_a'][dim]) for dim in nasa_dimensions]
    group_b_means = [np.mean(data_dict['nasa_dimensions']['group_b'][dim]) for dim in nasa_dimensions]

    # ===== Figure layout (1x3; third is polar) =====
    fig = plt.figure(figsize=(18, 6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1])
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2], projection='polar')

    # ===== Common legend handles =====
    legend_handles = [
        mpatches.Patch(color='blue',   label='Experiment Group'),
        mpatches.Patch(color='orange', label='Baseline Group')
    ]

    # ===== (a) SUS boxplot =====
    box1 = ax1.boxplot(sus_data, patch_artist=True, widths=0.2)
    # colors
    box1['boxes'][0].set_facecolor('blue')
    box1['boxes'][1].set_facecolor('orange')
    for med in box1['medians']:
        med.set_color('white'); med.set_linewidth(1.5)
    # axes
    ax1.set_title('(a)System Usability Scale (SUS)', fontsize=20, pad=10)
    ax1.set_ylabel('SUS Score (0–100)', fontsize=16)
    ax1.set_xlabel('Group', fontsize=16)
    ax1.set_xticks([1, 2]); ax1.set_xticklabels([])  # 不显示组名，使用图例区分
    ax1.tick_params(axis='both', which='major', labelsize=14)
    ax1.set_ylim(30, 100)
    ax1.grid(True, axis='y', alpha=0.3)
    ax1.legend(handles=legend_handles, loc='lower right', fontsize=12, frameon=True)

    # ===== (b) NASA-TLX boxplot =====
    box2 = ax2.boxplot(nasa_data, patch_artist=True, widths=0.2)
    box2['boxes'][0].set_facecolor('blue')
    box2['boxes'][1].set_facecolor('orange')
    for med in box2['medians']:
        med.set_color('white'); med.set_linewidth(1.5)
    ax2.set_title('(b)NASA Task Load Index (NASA-TLX)', fontsize=20, pad=10)
    ax2.set_ylabel('NASA-TLX Score (0–10)', fontsize=16)
    ax2.set_xlabel('Group', fontsize=16)
    ax2.set_xticks([1, 2]); ax2.set_xticklabels([])  # 不显示组名，使用图例区分
    ax2.tick_params(axis='both', which='major', labelsize=14)
    ax2.set_ylim(2, 8)
    ax2.grid(True, axis='y', alpha=0.3)
    ax2.legend(handles=legend_handles, loc='lower right', fontsize=12, frameon=True)

    # ===== (c) NASA-TLX radar =====
    N = len(nasa_dimensions)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # 闭合
    group_a_data = group_a_means + [group_a_means[0]]
    group_b_data = group_b_means + [group_b_means[0]]

    ax3.plot(angles, group_a_data, linewidth=2, linestyle='solid', label='Experiment Group', color='blue')
    ax3.fill(angles, group_a_data, alpha=0.25, color='blue')
    ax3.plot(angles, group_b_data, linewidth=2, linestyle='solid', label='Baseline Group', color='orange')
    ax3.fill(angles, group_b_data, alpha=0.25, color='orange')

    ax3.set_xticks(angles[:-1])
    ax3.set_xticklabels(nasa_dimensions, fontsize=14)
    ax3.tick_params(axis='y', which='major', labelsize=12)
    ax3.set_ylim(0, 10)
    ax3.set_title('(c)NASA-TLX Dimensions Comparison', fontsize=20, pad=12)
    ax3.legend(loc='upper right', bbox_to_anchor=(0.75, 0.9), fontsize=12, frameon=True)

    # ===== Panel labels (a)(b)(c) =====
    # for ax, label in zip([ax1, ax2, ax3], ['(a)', '(b)', '(c)']):
    #     ax.text(-0.12, 1.05, label, transform=ax.transAxes, fontsize=16, fontweight='bold',
    #             va='bottom', ha='left')

    # ===== Save & show =====
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.tight_layout()
    fig.savefig(save_path, dpi=dpi, bbox_inches='tight')
    fig.savefig(save_path.replace('.png', '.pdf'), format='pdf', bbox_inches='tight')
    plt.show()
    return fig, (ax1, ax2, ax3)

if __name__ == '__main__':
    # Load data
    data = load_data('Data_Analyze/questionnaire/processed_survey_data.json')

    # Prepare data for visualization
    data_dict = prepare_data_for_boxplot(data)

    # data_dict 按你现有结构传入
    create_combined_figure(data_dict, save_path='Data_Analyze/questionnaire/sus_nasa_combined.png')
