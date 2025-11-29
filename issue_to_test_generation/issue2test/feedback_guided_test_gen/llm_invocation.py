import time
import random
import logging
import litellm
import config
import runtime_state_tracking
import config


class LLMInvocation:
    def __init__(self, model: str):
        self.model = model

    def call_model(self, prompt: dict,
                   model_explicit=None,
                   max_tokens=4096,
                   temperature=0.2):
        """
        Calls the LLM model via LiteLLM and logs detailed statistics.

        Returns:
            tuple: (response text, prompt token count, completion token count, model_response_stats)
        Raises:
            RuntimeError: If the maximum number of retries is exceeded.
        """
        use_model = self.model

        if model_explicit is not None:
            use_model = model_explicit

        if "system" not in prompt or "user" not in prompt:
            raise KeyError("The prompt dictionary must contain 'system' and 'user' keys.")

        messages = [{"role": "user", "content": prompt["user"]}]
        if prompt["system"]:
            messages.insert(0, {"role": "system", "content": prompt["system"]})

        completion_params = {
            "model": use_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
            "temperature": temperature,
        }

        max_retries = 5
        base_delay = 2  # Initial delay in seconds

        for attempt in range(max_retries):
            try:
                logging.info(f"Invoking {self.model} with prompt: {messages}")
                response = litellm.completion(**completion_params)

                chunks = []
                try:
                    for chunk in response:
                        content = chunk.choices[0].delta.content or ""
                        chunks.append(chunk)
                        time.sleep(0.01)  # Simulating streaming delay
                except Exception as e:
                    logging.error(f"Streaming error: {e}")

                model_response = litellm.stream_chunk_builder(chunks, messages=messages)

                # Extract statistics
                prompt_tokens = int(model_response["usage"]["prompt_tokens"])
                completion_tokens = int(model_response["usage"]["completion_tokens"])
                litellm_cost = model_response["usage"].get("cost", 0.0)
                latency = model_response.get("latency_ms", 0.0)  # If LiteLLM provides latency
                request_id = model_response.get("request_id", "N/A")

                # Compute cost manually based on model pricing
                calculated_cost = self.calculate_cost(self.model, prompt_tokens, completion_tokens)
                runtime_state_tracking.calculated_cost = runtime_state_tracking.calculated_cost + calculated_cost
                runtime_state_tracking.litellm_reported_cost = runtime_state_tracking.litellm_reported_cost + litellm_cost

                # Model response statistics (POJO)
                model_response_stats = {
                    "model": self.model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "calculated_cost": round(calculated_cost, 15),
                    "litellm_reported_cost": round(litellm_cost, 15),
                    "latency_ms": round(latency, 3),
                    "request_id": request_id,
                }

                # Log all statistics in a single JSON-like format
                logging.info(f"Model Response Stats: {model_response_stats}")

                return (
                    model_response["choices"][0]["message"]["content"],
                    prompt_tokens,
                    completion_tokens,
                    model_response_stats
                )

            except litellm.RateLimitError as e:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logging.warning(
                    f"Rate limit exceeded (attempt {attempt + 1}/{max_retries}). Retrying in {delay:.2f} sec. Error: {e}")
                time.sleep(delay)

            except litellm.APIError as e:
                logging.error(f"API error while calling {self.model}: {e}")
                raise RuntimeError(f"API error while calling {self.model}: {e}")

            except litellm.InvalidRequestError as e:
                if "maximum context length" in str(e).lower():
                    logging.error(f"Context window exceeded for {self.model}. Reduce prompt size. Error: {e}")
                else:
                    logging.error(f"Invalid request error: {e}")
                raise RuntimeError(f"Invalid request error: {e}")

            except litellm.Timeout as e:
                logging.error(f"Request timed out. Error: {e}")
                raise RuntimeError(f"Request timed out: {e}")

            except Exception as e:
                logging.critical(f"Unexpected error on attempt {attempt + 1}: {e}")
                raise RuntimeError(f"Unexpected error: {e}")

        logging.error("Max retries exceeded. Could not complete API call.")
        raise RuntimeError("Max retries exceeded. Could not complete API call.")

    @staticmethod
    def calculate_cost(model_name, prompt_tokens, completion_tokens):
        """
        Calculates cost based on OpenAI pricing.
        """
        pricing = {
            "gpt-4o-mini": {"input": 0.15 / 1_000_000, "cached_input": 0.075 / 1_000_000, "output": 0.60 / 1_000_000},
            "gpt-4o-mini-2024-07-18": {"input": 0.15 / 1_000_000, "cached_input": 0.075 / 1_000_000,
                                       "output": 0.60 / 1_000_000},
        }

        if model_name not in pricing:
            logging.warning(f"Model {model_name} not found in pricing table.")
            return 0.0

        model_pricing = pricing[model_name]

        input_cost = prompt_tokens * model_pricing["input"]
        output_cost = completion_tokens * model_pricing["output"]
        total_cost = input_cost + output_cost

        return total_cost
