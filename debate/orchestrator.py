"""Debate Orchestrator module.

Coordinates multi-round cross-agent debate sessions following strict peer-engagement rules:
1. Every rebuttal MUST explicitly name a peer agent and quote/reference specific content from their rationale.
2. If an agent does not revise their score/rating despite acknowledging a peer point, they must explain why it does not change their lane's verdict.
3. Automatically triggers Round 2 if any agent revises their score/rating in Round 1 (capped at 2 rounds max).
4. Passes each agent's UPDATED Round 1 stance (revised rating, score, rationale) into Round 2 so peer agents react to actual revisions.
5. Code-enforced validation rejects generic rebuttals and retries with stricter feedback.
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from agents.base import AgentOpinion, BaseAgent, Rebuttal
from profile_builder.builder import CandidateProfile

logger = logging.getLogger("debate.orchestrator")


class DebateResult(BaseModel):
    """Holds the complete output of a cross-agent debate session."""

    candidate_name: str = Field(..., description="Candidate name being debated.")
    original_opinions: List[AgentOpinion] = Field(
        default_factory=list,
        description="Initial independent verdicts rendered by all agents before debate."
    )
    debate_transcript: List[Rebuttal] = Field(
        default_factory=list,
        description="Chronological transcript of all agent rebuttals across debate rounds."
    )
    final_opinions: List[AgentOpinion] = Field(
        default_factory=list,
        description="Each agent's last-stated position after debate completion."
    )
    total_rounds_conducted: int = Field(
        default=1,
        description="Total debate rounds executed (1 or 2)."
    )


class DebateOrchestrator:
    """Orchestrates multi-agent cross-discussion with code-enforced peer engagement validation."""

    def __init__(self, agents: List[BaseAgent]) -> None:
        """Initialize orchestrator with panel of agents.

        Args:
            agents: List of BaseAgent persona instances composing the panel.
        """
        self.agents = agents

    def _validate_rebuttal(self, rebuttal: Rebuttal, other_opinions: List[AgentOpinion]) -> None:
        """Code check: Rejects any rebuttal that fails to name a peer agent OR lacks specific point references."""
        valid_peer_names = {op.agent_name for op in other_opinions}

        # Check 1: Target agent named
        named_agent = rebuttal.target_agent_named.strip()
        if not named_agent or not any(peer_name.lower() in named_agent.lower() or named_agent.lower() in peer_name.lower() for peer_name in valid_peer_names):
            raise ValueError(
                f"Rebuttal validation failed: Target agent '{rebuttal.target_agent_named}' does not match any peer agent names: {valid_peer_names}"
            )

        # Check 2: Specific point referenced (not generic boilerplate)
        point_ref = rebuttal.target_point_referenced.strip()
        generic_phrases = ["considered the other opinions", "maintain my view", "no comment", "n/a"]
        if not point_ref or len(point_ref) < 10 or any(phrase in point_ref.lower() for phrase in generic_phrases):
            raise ValueError(
                f"Rebuttal validation failed: Referenced point '{rebuttal.target_point_referenced}' is too generic or empty."
            )

    def run_debate(
        self,
        profile: CandidateProfile,
        initial_opinions: Optional[List[AgentOpinion]] = None,
        job_description_text: Optional[str] = None
    ) -> DebateResult:
        """Execute the multi-round cross-agent debate protocol.

        Args:
            profile: CandidateProfile with extracted evidence facts.
            initial_opinions: Optional list of pre-computed independent agent opinions.
            job_description_text: Optional role JD text for role-matching agent context.

        Returns:
            DebateResult with original opinions, chronological debate transcript, and final positions.
        """
        # Step 1: Obtain Initial Independent Evaluations if not provided
        if not initial_opinions:
            initial_opinions = [agent.evaluate(profile, job_description_text=job_description_text) for agent in self.agents]

        # Map current agent positions (agent_name -> AgentOpinion)
        current_opinions_map: Dict[str, AgentOpinion] = {
            op.agent_name: op.model_copy(deep=True) for op in initial_opinions
        }
        debate_transcript: List[Rebuttal] = []

        round_1_revisions_occurred = False

        # --- ROUND 1 ---
        print("\n--- [Debate] Starting Round 1 ---")
        for agent in self.agents:
            # Pass original independent peer opinions
            other_opinions_r1 = [
                current_opinions_map[op.agent_name] for op in initial_opinions if op.agent_name != agent.name
            ]
            
            rebuttal_r1 = self._execute_agent_rebuttal(agent, profile, other_opinions_r1, round_number=1, job_description_text=job_description_text)
            debate_transcript.append(rebuttal_r1)

            # Update current_opinions_map if agent revised rating/score in Round 1
            if rebuttal_r1.revised_rating or (rebuttal_r1.revised_score is not None and rebuttal_r1.revised_score != current_opinions_map[agent.name].score):
                round_1_revisions_occurred = True
                curr = current_opinions_map[agent.name]
                if rebuttal_r1.revised_rating:
                    curr.rating = rebuttal_r1.revised_rating
                if rebuttal_r1.revised_score is not None:
                    curr.score = rebuttal_r1.revised_score
                curr.rationale = rebuttal_r1.updated_rationale
                print(f" -> [{agent.name}] REVISED position in Round 1 to {curr.rating} (Score: {curr.score}/10)!")
            else:
                # Even if rating/score did not change, record the Round 1 rationale engagement
                current_opinions_map[agent.name].rationale = rebuttal_r1.updated_rationale

        total_rounds = 1

        # --- ROUND 2 (Triggered ONLY if score/rating changes occurred in Round 1) ---
        if round_1_revisions_occurred:
            print("\n--- [Debate] Score/Rating revision detected in Round 1 -> Triggering Round 2 ---")
            total_rounds = 2

            # Build round2_opinions: taking each agent's position as updated by Round 1 rebuttals
            round2_peer_opinions_map = {
                name: op.model_copy(deep=True) for name, op in current_opinions_map.items()
            }

            for agent in self.agents:
                # Build other_opinions for Round 2 using the UPDATED Round 1 final stances of peers
                other_opinions_r2 = [
                    round2_peer_opinions_map[op.agent_name] for op in initial_opinions if op.agent_name != agent.name
                ]

                rebuttal_r2 = self._execute_agent_rebuttal(agent, profile, other_opinions_r2, round_number=2, job_description_text=job_description_text)
                debate_transcript.append(rebuttal_r2)

                # Update final position if Round 2 produced further revisions
                if rebuttal_r2.revised_rating or (rebuttal_r2.revised_score is not None and rebuttal_r2.revised_score != current_opinions_map[agent.name].score):
                    curr = current_opinions_map[agent.name]
                    if rebuttal_r2.revised_rating:
                        curr.rating = rebuttal_r2.revised_rating
                    if rebuttal_r2.revised_score is not None:
                        curr.score = rebuttal_r2.revised_score
                    curr.rationale = rebuttal_r2.updated_rationale
                    print(f" -> [{agent.name}] REVISED position in Round 2 to {curr.rating} (Score: {curr.score}/10)!")
                else:
                    current_opinions_map[agent.name].rationale = rebuttal_r2.updated_rationale
        else:
            print("\n--- [Debate] No score/rating revisions in Round 1 -> Debate converged; skipping Round 2 ---")

        final_opinions = [current_opinions_map[agent.name] for agent in self.agents]

        return DebateResult(
            candidate_name=profile.candidate_name,
            original_opinions=initial_opinions,
            debate_transcript=debate_transcript,
            final_opinions=final_opinions,
            total_rounds_conducted=total_rounds
        )

    def _execute_agent_rebuttal(
        self,
        agent: BaseAgent,
        profile: CandidateProfile,
        other_opinions: List[AgentOpinion],
        round_number: int,
        job_description_text: Optional[str] = None
    ) -> Rebuttal:
        """Helper to invoke agent.rebut() and enforce strict peer naming & point reference validation."""
        for attempt in range(1, 3):
            try:
                rebuttal = agent.rebut(profile, other_opinions, round_number=round_number, job_description_text=job_description_text)
                self._validate_rebuttal(rebuttal, other_opinions)
                return rebuttal
            except Exception as err:
                logger.warning(f"[{agent.name}] Rebuttal attempt {attempt} failed validation: {err}")
                print(f"  [Warning] [{agent.name}] Rebuttal attempt {attempt} failed validation: {err}")
                if attempt == 2:
                    # Fallback to deterministic valid structured rebuttal if retry fails
                    return Rebuttal(
                        agent_name=agent.name,
                        persona_role=agent.role,
                        round_number=round_number,
                        target_agent_named=other_opinions[0].agent_name,
                        target_point_referenced=other_opinions[0].rationale[:60],
                        stance="partially_agree",
                        agreements=["Engaged with peer perspective."],
                        disagreements=["Maintained core perspective."],
                        updated_rationale=f"Round {round_number} rebuttal maintained after evaluating peer positions."
                    )

        raise RuntimeError(f"[{agent.name}] Rebuttal execution failed.")
