import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

LOG_PATH = "logs/monitor.csv"

def clean_monitor_data(csv_path):
    # Read the raw CSV content
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    
    # Skip comment lines and clean data
    cleaned_lines = []
    header_found = False
    
    for line in lines:
        if line.startswith('#'):
            continue
        if not header_found:
            if 'r,l,t' in line:
                header_found = True
            continue
        
        # Clean the line of any corrupted data
        try:
            reward = float(line.split(',')[0].strip())
            cleaned_lines.append(f"{reward},100,0")  # Simplified format
        except (ValueError, IndexError):
            continue
    
    # Create DataFrame directly from cleaned data
    df = pd.DataFrame([line.split(',') for line in cleaned_lines], 
                     columns=['reward', 'length', 'timestamp'])
    
    # Convert to proper numeric types
    df['reward'] = pd.to_numeric(df['reward'], errors='coerce')
    df = df.dropna(subset=['reward'])
    
    return df

def main():
    # Read and clean data
    df = clean_monitor_data(LOG_PATH)
    
    if len(df) == 0:
        print("No valid data found in the log file!")
        return

    # Create the plot
    plt.figure(figsize=(15, 8))
    
    # Plot raw data points
    plt.scatter(df.index, df['reward'], alpha=0.2, color='gray', s=5, label='Episodes')
    
    # Calculate and plot moving averages
    window_sizes = [20, 50]
    colors = ['blue', 'red']
    
    for window, color in zip(window_sizes, colors):
        ma = df['reward'].rolling(window=window, min_periods=1).mean()
        plt.plot(df.index, ma, color=color, linewidth=2, 
                label=f'{window}-episode Moving Average')

    # Customize the plot
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xlabel('Episode', fontsize=12)
    plt.ylabel('Reward', fontsize=12)
    plt.title('PPO Learning Curve', fontsize=14)
    plt.legend(fontsize=10)

    # Add mean line
    mean_reward = df['reward'].mean()
    plt.axhline(y=mean_reward, color='green', linestyle='--', alpha=0.5)
    plt.text(len(df)*0.02, mean_reward, f'Mean: {mean_reward:.1f}', 
             verticalalignment='bottom')

    plt.tight_layout()
    plt.savefig('learning_curve.png', dpi=300, bbox_inches='tight')
    plt.show()

    # Print statistics
    print(f"Total episodes: {len(df)}")
    print(f"Average reward: {mean_reward:.2f}")
    print(f"Max reward: {df['reward'].max():.2f}")
    print(f"Min reward: {df['reward'].min():.2f}")

if __name__ == "__main__":
    main()