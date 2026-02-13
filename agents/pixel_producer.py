"""
Pixel Production Pipeline — Job-driven video production.

Full pipeline: job received → plan → approval → produce in Focal → review → deliver.

Every production goes through the approval queue. Jono always has final say
before credits are spent. Quality review uses Gemini to watch the output.
If quality is below 7/10, Pixel re-renders with adjustments (max 3 attempts).

Job states: received → planned → approved → producing → reviewing → delivered | failed
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

JOBS_DB_PATH = Path("data/pixel_jobs.db")
PORTFOLIO_DIR = Path("data/pixel_portfolio")

# Maximum render attempts before giving up
MAX_RENDER_ATTEMPTS = 3

# Minimum quality score for delivery
MIN_DELIVERY_SCORE = 7.0


@dataclass
class ProductionJob:
    """A video production job."""
    id: int
    title: str
    description: str            # Full job description / brief
    script: str                 # Video script or prompt
    model: str                  # Preferred video model (or "auto")
    duration_seconds: int       # Target duration
    status: str                 # received/planned/approved/producing/reviewing/delivered/failed
    production_plan: str        # JSON: detailed production plan
    quality_scores: str         # JSON: quality review results
    render_attempts: int        # How many renders attempted
    video_path: str             # Path to final video
    credits_used: int           # Total credits consumed
    cost_estimate: int          # Estimated credits before starting
    submitted_by: str           # Who submitted (jono, fiverr, etc.)
    approval_id: int | None     # Link to ApprovalQueue entry
    created_at: str
    updated_at: str
    delivered_at: str | None


class PixelProducer:
    """
    Video production pipeline.

    Manages the full lifecycle of a video production job:
    1. Receive job (from Telegram, future: Fiverr/Upwork)
    2. Create production plan (model, settings, estimated credits)
    3. Submit plan for human approval
    4. On approval: execute in Focal ML
    5. Quality review via Gemini
    6. Re-render if needed (max 3 attempts)
    7. Deliver final video
    """

    def __init__(
        self,
        browser,
        reviewer,
        knowledge_store,
        approval_queue=None,
        audit_log=None,
    ):
        self.browser = browser
        self.reviewer = reviewer
        self.knowledge = knowledge_store
        self.approval_queue = approval_queue
        self.audit_log = audit_log
        self._init_db()

        PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(JOBS_DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the jobs database."""
        JOBS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                script TEXT DEFAULT '',
                model TEXT DEFAULT 'auto',
                duration_seconds INTEGER DEFAULT 30,
                status TEXT DEFAULT 'received',
                production_plan TEXT DEFAULT '{}',
                quality_scores TEXT DEFAULT '{}',
                render_attempts INTEGER DEFAULT 0,
                video_path TEXT DEFAULT '',
                credits_used INTEGER DEFAULT 0,
                cost_estimate INTEGER DEFAULT 0,
                submitted_by TEXT DEFAULT 'operator',
                approval_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                delivered_at TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)
        """)
        conn.commit()
        conn.close()
        logger.info("Pixel jobs database initialized")

    # ------------------------------------------------------------------
    # Job lifecycle
    # ------------------------------------------------------------------

    def create_job(
        self,
        title: str,
        description: str = "",
        script: str = "",
        model: str = "auto",
        duration_seconds: int = 30,
        submitted_by: str = "operator",
    ) -> int:
        """
        Create a new production job.

        Returns job_id.
        """
        conn = self._get_conn()
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """INSERT INTO jobs (title, description, script, model, duration_seconds,
                               submitted_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, description, script, model, duration_seconds, submitted_by, now, now),
        )
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Job #{job_id} created: {title}")

        if self.audit_log:
            self.audit_log.log(
                "pixel", "info", "job",
                f"Job created: {title}",
                details=f"id={job_id}, model={model}, duration={duration_seconds}s",
            )

        return job_id

    def get_job(self, job_id: int) -> ProductionJob | None:
        """Get a job by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return self._to_job(row)

    def get_jobs_by_status(self, status: str) -> list[ProductionJob]:
        """Get all jobs with a given status."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
        conn.close()
        return [self._to_job(r) for r in rows]

    def _update_job(self, job_id: int, **kwargs):
        """Update job fields."""
        kwargs["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [job_id]

        conn = self._get_conn()
        conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", values)
        conn.commit()
        conn.close()

    async def create_production_plan(self, job_id: int) -> dict:
        """
        Create a production plan for a job.

        Queries the knowledge base for the best approach, then creates
        a plan with model selection, settings, and cost estimate.

        Returns the plan dict and updates the job status to 'planned'.
        """
        job = self.get_job(job_id)
        if not job:
            return {"error": f"Job #{job_id} not found"}

        # Query knowledge base for relevant info
        model_knowledge = self.knowledge.search(
            f"Focal ML {job.model} model" if job.model != "auto" else "Focal ML video model",
            category="technical",
            limit=5,
        )

        credit_knowledge = self.knowledge.search(
            "credit cost per second",
            category="technical",
            limit=3,
        )

        # Build plan
        plan = {
            "job_id": job_id,
            "title": job.title,
            "model": job.model if job.model != "auto" else "seedance",  # Default to seedance
            "duration_seconds": job.duration_seconds,
            "estimated_credits": self._estimate_credits(job.model, job.duration_seconds),
            "steps": [
                "Create new Focal ML project",
                f"Enter script ({len(job.script)} chars)" if job.script else "Enter prompt from description",
                f"Select video model: {job.model}",
                "Configure quality settings",
                "Start render",
                "Wait for completion",
                "Download video",
                "Quality review via Gemini",
            ],
            "knowledge_context": [
                {"topic": k.topic, "content": k.content[:200]}
                for k in model_knowledge
            ],
            "created_at": datetime.now().isoformat(),
        }

        # Update job
        self._update_job(
            job_id,
            status="planned",
            production_plan=json.dumps(plan),
            cost_estimate=plan["estimated_credits"],
        )

        logger.info(
            f"Job #{job_id} planned: {plan['model']}, "
            f"~{plan['estimated_credits']} credits, "
            f"{plan['duration_seconds']}s video"
        )

        return plan

    async def submit_for_approval(self, job_id: int) -> int | None:
        """
        Submit a planned job for human approval.

        Returns approval_id, or None if no approval queue configured.
        """
        job = self.get_job(job_id)
        if not job or job.status != "planned":
            logger.error(f"Job #{job_id} not in 'planned' state")
            return None

        if not self.approval_queue:
            logger.warning("No approval queue — auto-approving (NOT RECOMMENDED)")
            self._update_job(job_id, status="approved")
            return None

        plan = json.loads(job.production_plan)

        approval_id = self.approval_queue.submit(
            project_id="pixel",
            agent_id="pixel-producer",
            action_type="video_production",
            action_data={
                "job_id": job_id,
                "title": job.title,
                "model": plan.get("model", "auto"),
                "duration": plan.get("duration_seconds", 30),
                "estimated_credits": plan.get("estimated_credits", 0),
                "script_preview": job.script[:300] if job.script else job.description[:300],
            },
            context_summary=(
                f"Pixel video production: {job.title} | "
                f"{plan.get('model', '?')} model, ~{plan.get('estimated_credits', '?')} credits"
            ),
            cost_estimate=plan.get("estimated_credits", 0) * 0.01,  # Rough USD estimate
        )

        self._update_job(job_id, approval_id=approval_id)
        logger.info(f"Job #{job_id} submitted for approval (approval #{approval_id})")
        return approval_id

    async def produce_video(self, job_id: int) -> dict:
        """
        Execute the full production pipeline for an approved job.

        1. Open Focal ML → create project → enter script → configure → render
        2. Download the result
        3. Run quality review
        4. Re-render if score < 7 (up to MAX_RENDER_ATTEMPTS)
        5. Save to portfolio if score >= 8

        Returns dict with 'success', 'video_path', 'quality_score', 'attempts'
        """
        job = self.get_job(job_id)
        if not job:
            return {"success": False, "error": f"Job #{job_id} not found"}

        if job.status not in ("approved", "producing"):
            return {"success": False, "error": f"Job #{job_id} not in approved state (is: {job.status})"}

        self._update_job(job_id, status="producing")
        plan = json.loads(job.production_plan) if job.production_plan else {}

        best_video = None
        best_score = None
        total_credits = 0

        for attempt in range(1, MAX_RENDER_ATTEMPTS + 1):
            logger.info(f"Job #{job_id}: Render attempt {attempt}/{MAX_RENDER_ATTEMPTS}")
            self._update_job(job_id, render_attempts=attempt)

            # Track credits
            credits_before = await self.browser.get_credit_balance()

            # Execute production in Focal ML
            render_result = await self._execute_in_focal(job, plan, attempt)

            credits_after = await self.browser.get_credit_balance()
            if credits_before is not None and credits_after is not None:
                total_credits += max(0, credits_before - credits_after)

            if not render_result.get("success"):
                logger.warning(f"Render attempt {attempt} failed: {render_result.get('error')}")
                if self.audit_log:
                    self.audit_log.log(
                        "pixel", "warn", "render",
                        f"Render failed for job #{job_id} (attempt {attempt})",
                        details=render_result.get("error", ""),
                    )
                continue

            video_path = render_result.get("video_path")
            if not video_path:
                continue

            # Quality review
            self._update_job(job_id, status="reviewing")
            score = await self.reviewer.review_video(
                video_path=video_path,
                script=job.script,
                context={
                    "model": plan.get("model", "unknown"),
                    "duration": plan.get("duration_seconds", "unknown"),
                    "attempt": attempt,
                },
            )

            logger.info(
                f"Job #{job_id} attempt {attempt}: score {score.overall:.1f}/10 "
                f"({score.recommendation})"
            )

            # Track best result
            if best_score is None or score.overall > best_score.overall:
                best_video = video_path
                best_score = score

            # Good enough?
            if score.overall >= MIN_DELIVERY_SCORE:
                break

            # Not good enough — adjust plan for next attempt
            if attempt < MAX_RENDER_ATTEMPTS:
                plan["adjustments"] = score.regeneration_notes
                logger.info(f"Re-rendering with adjustments: {score.regeneration_notes[:100]}")

        # Finalize
        if best_score and best_score.overall >= MIN_DELIVERY_SCORE:
            # Success — deliver
            self._update_job(
                job_id,
                status="delivered",
                video_path=str(best_video),
                credits_used=total_credits,
                quality_scores=json.dumps(best_score.to_dict()),
                delivered_at=datetime.now().isoformat(),
            )

            # Portfolio?
            if self.reviewer.should_add_to_portfolio(best_score):
                self._add_to_portfolio(best_video, job)

            if self.audit_log:
                self.audit_log.log(
                    "pixel", "info", "production",
                    f"Job #{job_id} delivered: {best_score.overall:.1f}/10",
                    details=f"credits={total_credits}, attempts={job.render_attempts}",
                )

            return {
                "success": True,
                "video_path": str(best_video),
                "quality_score": best_score.overall,
                "attempts": attempt,
                "credits_used": total_credits,
            }
        else:
            # Failed — all attempts below threshold
            self._update_job(
                job_id,
                status="failed",
                credits_used=total_credits,
                quality_scores=json.dumps(best_score.to_dict()) if best_score else "{}",
            )

            if self.audit_log:
                self.audit_log.log(
                    "pixel", "reject", "production",
                    f"Job #{job_id} failed after {MAX_RENDER_ATTEMPTS} attempts",
                    details=f"best_score={best_score.overall:.1f if best_score else 0}",
                    success=False,
                )

            return {
                "success": False,
                "error": f"All {MAX_RENDER_ATTEMPTS} attempts below quality threshold",
                "best_score": best_score.overall if best_score else 0,
                "video_path": str(best_video) if best_video else None,
                "credits_used": total_credits,
            }

    async def _execute_in_focal(self, job: ProductionJob, plan: dict, attempt: int) -> dict:
        """
        Execute the actual video production in Focal ML browser.

        Returns dict with 'success', 'video_path', 'error'
        """
        model = plan.get("model", "seedance")
        adjustments = plan.get("adjustments", "")

        # Step 1: Create new project
        result = await self.browser.run_task(
            "Create a new video project in Focal ML. "
            "Click the 'Create' or 'New Project' button."
        )
        if not result["success"]:
            return {"success": False, "error": "Failed to create project"}

        # Step 2: Enter script
        script = job.script or job.description
        if adjustments and attempt > 1:
            script += f"\n\nADJUSTMENTS: {adjustments}"

        if not await self.browser.enter_script(script):
            return {"success": False, "error": "Failed to enter script"}

        # Step 3: Select model
        if not await self.browser.select_video_model(model):
            return {"success": False, "error": f"Failed to select model: {model}"}

        # Step 4: Configure and start render
        result = await self.browser.run_task(
            "Review the current settings. If everything looks correct, "
            "click the 'Generate' or 'Render' button to start video generation. "
            "Do NOT change settings unless something is clearly wrong."
        )
        if not result["success"]:
            return {"success": False, "error": "Failed to start render"}

        # Step 5: Wait for render
        render_result = await self.browser.wait_for_render(timeout_seconds=600)
        if not render_result["completed"]:
            return {"success": False, "error": render_result.get("error", "Render failed")}

        # Step 6: Download
        video_path = await self.browser.download_video(
            filename=f"job_{job.id}_attempt_{attempt}.mp4"
        )
        if not video_path:
            return {"success": False, "error": "Failed to download video"}

        return {"success": True, "video_path": video_path}

    def _estimate_credits(self, model: str, duration_seconds: int) -> int:
        """Estimate credit cost based on model and duration."""
        # Default estimates (updated as Pixel learns actual costs)
        cost_per_second = {
            "seedance": 4,
            "veo": 5,
            "kling": 4,
            "minimax": 3,
            "luma": 3,
            "runway": 5,
            "auto": 4,
        }
        rate = cost_per_second.get(model.lower(), 4)
        return rate * duration_seconds

    def _add_to_portfolio(self, video_path: Path | str, job: ProductionJob):
        """Copy a high-quality video to the portfolio directory."""
        import shutil
        src = Path(video_path)
        if src.exists():
            dest = PORTFOLIO_DIR / f"portfolio_{job.id}_{src.name}"
            shutil.copy2(src, dest)
            logger.info(f"Added to portfolio: {dest}")

    # ------------------------------------------------------------------
    # Job queue queries
    # ------------------------------------------------------------------

    def get_queue_status(self) -> dict:
        """Get overview of job queue."""
        conn = self._get_conn()
        status_counts = {}
        for status in ["received", "planned", "approved", "producing", "reviewing", "delivered", "failed"]:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM jobs WHERE status = ?", (status,)
            ).fetchone()
            count = row["cnt"]
            if count > 0:
                status_counts[status] = count

        total_credits = conn.execute(
            "SELECT COALESCE(SUM(credits_used), 0) as total FROM jobs"
        ).fetchone()["total"]

        conn.close()

        return {
            "by_status": status_counts,
            "total_credits_used": total_credits,
        }

    def _to_job(self, row) -> ProductionJob:
        return ProductionJob(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            script=row["script"],
            model=row["model"],
            duration_seconds=row["duration_seconds"],
            status=row["status"],
            production_plan=row["production_plan"],
            quality_scores=row["quality_scores"],
            render_attempts=row["render_attempts"],
            video_path=row["video_path"],
            credits_used=row["credits_used"],
            cost_estimate=row["cost_estimate"],
            submitted_by=row["submitted_by"],
            approval_id=row["approval_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            delivered_at=row["delivered_at"],
        )
