"""
LLM Integration module using OpenAI API.
"""
import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Ensure environment variables are loaded when this module is used independently
load_dotenv()

class KeywordExtraction(BaseModel):
    keywords: List[str] = Field(description="List of extracted job search keywords")

class JobRelevance(BaseModel):
    score: int = Field(description="Relevance score out of 100")
    reasoning: str = Field(description="Brief reasoning for the given score")

class ApplicationMaterials(BaseModel):
    cv_recommendations: str = Field(description="Markdown formatted expert recruiter advice on exactly what CV lines to add/change/highlight to secure an interview.")
    cover_letter: str = Field(description="A highly targeted, professional cover letter ready for the candidate to use.")

def get_client_and_model() -> tuple[OpenAI, str]:
    """Returns the configured OpenAI-compatible client and the model string."""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Neither LLM_API_KEY nor OPENAI_API_KEY environment variables are set.")
    
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # 1. Check if the user explicitly defined a BASE_URL
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    
    # 2. If not, dynamically select the URL based on the model name
    if not base_url:
        if "gemini" in model.lower():
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        else:
            base_url = None # Standard OpenAI endpoint
            
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model

def _call_llm_with_fallback(client: OpenAI, model: str, messages: List[Dict[str, str]], response_format: Any) -> Any:
    """Wrapper to handle 429 Rate Limits automatically with a fallback model and sleep."""
    import time
    fallback_model = os.getenv("FALLBACK_LLM_MODEL")
    attempts = 2
    
    for attempt in range(attempts):
        try:
            return client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=response_format,
            )
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "exhausted" in err_msg.lower() or "quota" in err_msg.lower():
                if attempt < attempts - 1:
                    wait_time = 16  # API requests 15s
                    print(f"\n[⚠️ 429 Rate Limit] Pacing model ({model}). Sleeping {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                elif fallback_model:
                    print(f"\n[🔄 Fallback] Exhausted retries for {model}, switching to fallback model: {fallback_model}...")
                    try:
                        return client.beta.chat.completions.parse(
                            model=fallback_model,
                            messages=messages,
                            response_format=response_format,
                        )
                    except Exception as fallback_e:
                        raise fallback_e
            # If not a 429 error or ran out of attempts and no fallback, throw it
            raise e

def deduce_keywords_from_cv(cv_text: str, num_keywords: int = 3) -> List[str]:
    """Uses LLM to extract primary job search keywords based on CV text."""
    client, model = get_client_and_model()
    prompt = f"Analyze the following CV and extract {num_keywords} comma-separated job titles or search keywords that would be highly relevant for this person's job search. Provide only the keywords.\n\nCV:\n{cv_text[:4000]}"
    
    response = _call_llm_with_fallback(
        client=client,
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert technical recruiter and career coach."},
            {"role": "user", "content": prompt}
        ],
        response_format=KeywordExtraction,
    )
    
    return response.choices[0].message.parsed.keywords

def expand_seed_keywords(seed_keywords: List[str], cv_text: str, num_expansions: int = 3) -> List[str]:
    """Takes approved seed keywords and uses the LLM to slightly expand the net with synonyms/related roles."""
    client, model = get_client_and_model()
    seeds_str = ", ".join(seed_keywords)
    prompt = f"The user has approved these core job search keywords: [{seeds_str}]. Based on their CV below, suggest {num_expansions} slightly different variations, synonyms, or related job titles that might capture highly relevant job postings they missed. ONLY return the new expanded keywords, do not include the original seeds.\n\nCV:\n{cv_text[:4000]}"
    
    try:
        response = _call_llm_with_fallback(
            client=client,
            model=model,
            messages=[
                {"role": "system", "content": "You are a technical recruiter. Return a list of short job titles/keywords."},
                {"role": "user", "content": prompt}
            ],
            response_format=KeywordExtraction,
        )
        return response.choices[0].message.parsed.keywords
    except:
        return []

def score_job_relevance(cv_text: str, job_description: str) -> Dict[str, Any]:
    """Scores a job description against a CV and returns score and reasoning."""
    client, model = get_client_and_model()
    prompt = f"Analyze this job description against the provided CV. Rate the match from 0 to 100 and explain why in 1-2 short sentences. Pay EXACT attention to the years of experience and seniority level required (e.g., Junior, Mid, Senior, Lead). Aggressively penalize the score (drop below 50) if the job demands team leadership, management, or a seniority level that the candidate clearly lacks.\n\nCV:\n{cv_text[:3000]}\n\nJob Description:\n{job_description[:3000]}"
    
    try:
        response = _call_llm_with_fallback(
            client=client,
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert HR sourcer matching candidates to jobs."},
                {"role": "user", "content": prompt}
            ],
            response_format=JobRelevance,
        )
        parsed = response.choices[0].message.parsed
        return {"score": parsed.score, "reasoning": parsed.reasoning}
    except Exception as e:
        return {"score": 0, "reasoning": f"Error scoring: {str(e)}"}

def generate_application_materials(cv_text: str, job_description: str) -> Dict[str, str]:
    """Uses LLM to act as recruiter (CV Tips) and applicant (Cover Letter) based on a high-matching job."""
    client, model = get_client_and_model() # Uses user's identical model as requested
    
    prompt = (
        "You are acting in a dual capacity: First as an expert technical recruiter, and second as the applicant.\n\n"
        "1. Read the following Job Description to determine its primary language (English or German).\n"
        "2. READ CAREFULLY: You MUST output BOTH the cv_recommendations and the cover_letter in that EXACT same detected language.\n"
        "3. Provide targeted cv_recommendations detailing exactly what the candidate should highlight, rewrite, or add to their CV to become the perfect match.\n"
        "4. Provide a professional, persuasive cover_letter targeted exactly to this job based on their CV.\n\n"
        f"CV:\n{cv_text[:4000]}\n\n"
        f"Job Description:\n{job_description[:4000]}"
    )

    try:
        response = _call_llm_with_fallback(
            client=client,
            model=model,
            messages=[
                {"role": "system", "content": "You are dual-role HR expert and professional ghostwriter. Ensure language matching."},
                {"role": "user", "content": prompt}
            ],
            response_format=ApplicationMaterials,
        )
        parsed = response.choices[0].message.parsed
        return {
            "cv_recommendations": parsed.cv_recommendations,
            "cover_letter": parsed.cover_letter
        }
    except Exception as e:
        print(f"\nFailed to generate application materials: {e}")
        return {
            "cv_recommendations": f"Error generating recommendations: {e}",
            "cover_letter": f"Error generating cover letter: {e}"
        }
