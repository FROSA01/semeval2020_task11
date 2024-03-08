def count_labels(filename):
    label_counts = {}

    with open(filename, 'r') as file:
        for line in file:
            columns = line.strip().split('\t')
            if len(columns) >= 2:
                labels = columns[1].split(',')
                for label in labels:
                    label_counts[label] = label_counts.get(label, 0) + 1

    return label_counts

def main():
    filename = 'results\TC_output_dev_sc.txt' 
    label_counts = count_labels(filename)

    for label, count in label_counts.items():
        print(f'{label}: {count}')

if __name__ == "__main__":
    main()