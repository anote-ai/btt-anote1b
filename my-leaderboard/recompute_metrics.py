"""
Re-compute metrics for all existing submissions

This script re-evaluates all completed submissions to compute
the new comprehensive metrics we've added.
"""
from database import SessionLocal, init_db
from models import Submission, Dataset, SubmissionStatus
from evaluators import get_evaluator
from datetime import datetime

def recompute_all_metrics():
    """Re-evaluate all submissions with updated evaluators"""
    init_db()
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("🔄 RE-COMPUTING METRICS FOR ALL SUBMISSIONS")
        print("="*60 + "\n")
        
        # Get all completed submissions
        submissions = db.query(Submission).filter(
            Submission.status == SubmissionStatus.COMPLETED
        ).all()
        
        print(f"Found {len(submissions)} submissions to re-evaluate\n")
        
        updated_count = 0
        
        for sub in submissions:
            # Get dataset
            dataset = db.query(Dataset).filter(Dataset.id == sub.dataset_id).first()
            if not dataset:
                print(f"⚠️  Skipping {sub.id} - dataset not found")
                continue
            
            try:
                # Get evaluator
                evaluator = get_evaluator(dataset.task_type.value)
                
                # Re-run evaluation
                scores = evaluator.evaluate(dataset.ground_truth, sub.predictions)
                
                # Update submission with new comprehensive scores
                sub.detailed_scores = scores
                sub.primary_score = scores.get(dataset.primary_metric, sub.primary_score)
                
                updated_count += 1
                
                print(f"✓ {sub.model_name} on {dataset.name[:40]}")
                print(f"  Metrics: {', '.join(scores.keys())}")
                
            except Exception as e:
                print(f"✗ Failed to re-evaluate {sub.id}: {e}")
        
        db.commit()
        
        print("\n" + "="*60)
        print(f"✅ RE-COMPUTATION COMPLETE!")
        print("="*60)
        print(f"\n📊 Updated {updated_count} submissions")
        print("🔄 Refresh your browser to see the new metrics\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    recompute_all_metrics()

