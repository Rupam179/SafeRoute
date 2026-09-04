"""
SafeRoute — YOLOv8 Road-Damage Training Script (template)
============================================================

This is the recipe for Phase 5 of the project plan ("AI Model Development").
Run this OUTSIDE the lightweight ai_service container — training needs
`ultralytics` + `torch` (and ideally a GPU / Colab), which are deliberately
NOT in ai_service/requirements.txt so the demo stack stays light.

Setup (local machine or Google Colab):
    pip install ultralytics

Steps:
    1. Download RDD2022 (or the CRDDC subset you're using) and your own
       150-300 collected photos.
    2. Organise as YOLO format:

        dataset/
          images/train/*.jpg
          images/val/*.jpg
          images/test/*.jpg        <- your OWN photos, held out, never trained on
          labels/train/*.txt
          labels/val/*.txt
          labels/test/*.txt
          data.yaml

       data.yaml example:
        path: ./dataset
        train: images/train
        val: images/val
        test: images/test
        names:
          0: longitudinal_crack
          1: transverse_crack
          2: alligator_crack
          3: pothole
          4: rutting

    3. Run this script:
        python train.py --data dataset/data.yaml --epochs 100 --imgsz 640

    4. Evaluate honestly on the held-out test split (your own photos):
        python train.py --evaluate-only --weights runs/detect/train/weights/best.pt --data dataset/data.yaml

    5. Copy the resulting best.pt into ai_service/weights/best.pt and
       restart the ai_service container — inference.py will pick it up
       automatically, no code changes required.

    6. Record the REAL precision/recall/F1 numbers (whatever they are) in
       docs/MODEL_EVALUATION.md — do not cherry-pick favourable examples.
"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--model", default="yolov8n.pt", help="Pretrained checkpoint to fine-tune from")
    parser.add_argument("--evaluate-only", action="store_true")
    parser.add_argument("--weights", help="Weights to evaluate (with --evaluate-only)")
    args = parser.parse_args()

    from ultralytics import YOLO  # imported lazily so this file can be inspected without the dep installed

    if args.evaluate_only:
        if not args.weights:
            raise SystemExit("--weights is required with --evaluate-only")
        model = YOLO(args.weights)
        metrics = model.val(data=args.data, split="test")
        print("Precision:", metrics.box.mp)
        print("Recall:", metrics.box.mr)
        print("mAP50:", metrics.box.map50)
        print("mAP50-95:", metrics.box.map)
        return

    model = YOLO(args.model)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz)

    print("\nTraining complete. Evaluating on held-out test split...")
    metrics = model.val(data=args.data, split="test")
    print("Precision:", metrics.box.mp)
    print("Recall:", metrics.box.mr)
    print("mAP50:", metrics.box.map50)


if __name__ == "__main__":
    main()
