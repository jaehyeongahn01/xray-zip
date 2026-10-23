"""Evaluate the submitted checkpoint; never modifies the original final metrics."""
import argparse
import sys
from pathlib import Path
import pandas as pd
import torch
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '02_web_service' / 'streamlit'))
from inference import load_model, _eval_tf, DEVICE, CLASS_NAMES

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'03_model_and_results'/'reevaluation')
    args = parser.parse_args()
    frame = pd.read_csv(ROOT/'04_dataset'/'final_test_split.csv')
    model = load_model(ROOT/'03_model_and_results'/'best_model.pth')
    predictions = []
    with torch.no_grad():
        for rel in frame['relative_path']:
            with Image.open(args.data_root/rel) as image:
                tensor = _eval_tf(image.convert('RGB')).unsqueeze(0).to(DEVICE)
            predictions.append(int(model(tensor).argmax(1).item()))
    args.output.mkdir(parents=True, exist_ok=True)
    frame['prediction'] = predictions
    frame['correct'] = frame['label'] == frame['prediction']
    frame.to_csv(args.output/'predictions.csv', index=False, encoding='utf-8-sig')
    report = classification_report(frame['label'], predictions, labels=[0,1,2], target_names=CLASS_NAMES, output_dict=True, zero_division=0)
    pd.DataFrame(report).T.to_csv(args.output/'classification_report.csv', encoding='utf-8-sig')
    pd.DataFrame(confusion_matrix(frame['label'], predictions, labels=[0,1,2]), index=CLASS_NAMES, columns=CLASS_NAMES).to_csv(args.output/'confusion_matrix.csv', encoding='utf-8-sig')
    print('Evaluation saved:', args.output)

if __name__ == '__main__':
    main()
