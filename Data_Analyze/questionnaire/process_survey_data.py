import pandas as pd
import json

def process_survey_data(csv_file_path):
    """
    Process survey data and extract SUS, NASA-TLX, and CPSES scales
    """
    # Read the CSV file with encoding handling
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(csv_file_path, encoding='gbk')
    
    # Initialize the result dictionary
    result = {}
    
    # Process each row
    for index, row in df.iterrows():
        # Get the experiment ID
        exp_id = row['Please enter your experiment ID. ']
        
        # Skip if no experiment ID
        if pd.isna(exp_id) or exp_id == '':
            continue
            
        # Extract SUS data (10 items)
        # SUS starts from column "I think that I would like to use this system frequently." (C24)
        sus_columns = [
            "I think that I would like to use this system frequently.  ",
            "I found the system unnecessarily complex.  ",
            "I thought the system was easy to use. ",
            "I think that I would need the support of a technical person to be able to use this system. ",
            "I found the various functions in this system were well integrated. ",
            "I thought there was too much inconsistency in this system. ",
            "I would imagine that most people would learn to use this system very quickly. ",
            "I found the system very cumbersome to use. ",
            "I felt very confident using the system. ",
            "I needed to learn a lot of things before I could get going with this system. "
        ]
        
        sus_scores = []
        for col in sus_columns:
            score = row[col]
            # Handle missing values
            if pd.isna(score):
                score = 0
            sus_scores.append(int(score))
        
        # Extract NASA-TLX data (6 items)
        nasa_columns = [
            "  How much mental and perceptual activity was required (e.g., thinking, deciding, calculating, remembering, looking, searching, etc.)?  ",
            "How much physical activity was required (e.g., pushing, pulling, turning, controlling, activating, etc.)? ",
            "How much time pressure did you feel due to the rate or pace at which the tasks occurred? ",
            "How successful do you think you were in accomplishing the goals of the task set by the experimenter (or yourself)? How satisfied were you with your performance in accomplishing these goals? ",
            "How hard did you have to work (mentally and physically) to accomplish your level of performance? ",
            "How insecure, discouraged, irritated, stressed, and annoyed versus secure, gratified, content, relaxed, and complacent did you feel during the task? "
        ]
        
        nasa_scores = []
        for col in nasa_columns:
            score = row[col]
            # Handle missing values
            if pd.isna(score):
                score = 0
            nasa_scores.append(int(score))
        
        # Extract CPSES data (12 items)
        cpes_columns = [
            "  I can understand the basic logical structure of HTML, CSS, and JavaScript code.  ",
            "  I can understand how conditional statements (e.g., if...else) work with AI support.  ",
            "I can predict the result of a JavaScript program when given specific input values. ",
            "  I can identify and correct errors in my HTML, CSS, or JavaScript code with the help of AI.  ",
            "I can understand error messages and AI-generated explanations when my code does not run correctly. ",
            "I can improve my programming skills by learning from AI debugging suggestions. ",
            "I can write a simple web page using HTML, CSS, and JavaScript with AI guidance. ",
            "I can use AI to help me apply loops, conditions, or functions in JavaScript. ",
            "I can combine AI suggestions with my own knowledge to solve a programming task. ",
            "I feel confident that I can complete programming exercises with AI support. ",
            "I believe I can continue learning web development effectively with AI assistance. ",
            "I can work more efficiently by dividing tasks between myself and AI (e.g., I focus on design, AI helps with debugging). "
        ]
        
        cpes_scores = []
        for col in cpes_columns:
            score = row[col]
            # Handle missing values
            if pd.isna(score):
                score = 0
            cpes_scores.append(int(score))
        
        # Add to result dictionary
        result[exp_id] = {
            "SUS": sus_scores,
            "NASA-TLX": nasa_scores,
            "CPSES": cpes_scores
        }
    
    return result

def save_result_to_json(data, output_file):
    """
    Save the processed data to a JSON file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Process the survey data
    csv_file = "Untitled form.csv"
    output_file = "processed_survey_data.json"
    
    result = process_survey_data(csv_file)
    
    # Print the result
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Save to JSON file
    save_result_to_json(result, output_file)
    print(f"\nData has been processed and saved to {output_file}")