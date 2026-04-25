import asyncio
from app.evaluation.seed import synthetic_dependency_failure
from app.llm.orchestrator import RCAOrchestrator

async def main():
    try:
        print("Creating synthetic context...")
        ctx = synthetic_dependency_failure()
        ctx.id = "test-e2e-2"
        print("Running RCAOrchestrator...")
        rca = await RCAOrchestrator().process(ctx)
        print("Success!")
        print("Summary:", rca.summary)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
