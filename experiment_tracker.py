"""
Experiment tracker for garment simulation using MLflow.

Tracks rendered images, simulation parameters, and metrics for experiment
comparison and debugging purposes.

This class implements the Singleton pattern to ensure only one instance exists.
"""

import asyncio
import concurrent.futures
import logging
import os
import shutil
import tempfile
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Optional

import cv2
import mlflow
from mlflow.tracking import MlflowClient
import numpy as np

from log_config import set_log_level
from loguru import logger


class MLflowConfig:
    """Configuration for MLflow tracking."""
    
    def __init__(
        self,
        server_url: Optional[str] = None,
        remote_server_alias: Optional[str] = None,
        local_artifact_dir: str = "./mlruns",
        remote_artifact_uri: Optional[str] = None,
        remote_mlflow_path: Optional[str] = None,
        max_workers: int = 4,
        enabled: bool = True
    ):
        """Initialize MLflow configuration.
        
        Args:
            server_url: MLflow tracking server URL (e.g., "http://localhost:5000")
            remote_server_alias: SSH alias for remote server (e.g., "user@server")
            local_artifact_dir: Local directory for MLflow artifacts
            remote_artifact_uri: Remote path for artifacts (e.g., "/home/user/mlruns")
            remote_mlflow_path: Path to mlflow CLI on remote server
            max_workers: Number of worker threads for async operations
            enabled: Whether MLflow tracking is enabled
        """
        self.server_url = server_url
        self.remote_server_alias = remote_server_alias
        self.local_artifact_dir = local_artifact_dir
        self.remote_artifact_uri = remote_artifact_uri
        self.remote_mlflow_path = remote_mlflow_path
        self.max_workers = max_workers
        self.enabled = enabled


class ExperimentTracker:
    """Tracks and logs experiment results for garment simulation.
    
    Handles logging of rendered images, simulation parameters, and metrics
    to both local storage and MLflow for experiment tracking and debugging.
    
    This class implements the Singleton pattern to ensure only one instance exists.
    """
    
    _instance = None
    _initialized = False
    _config: Optional[MLflowConfig] = None
    _exp_name: str = "temp_exp"
    _active_run: Optional[mlflow.ActiveRun] = None
    _mlflow_images_dir: Optional[Path] = None
    _temp_artifact_dir: Optional[str] = None
    _local_artifact_dir: Optional[str] = None
    _remote_artifact_uri: Optional[str] = None
    _remote_server_alias: Optional[str] = None
    _mlflow_server: Optional[str] = None
    _executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
    _client: Optional[MlflowClient] = None
    _max_workers: int = 4
    _has_errors: bool = False
    _pending_tasks: list[concurrent.futures.Future[Any]] = []
    
    def __new__(cls, mlflow_config: Optional[MLflowConfig] = None, exp_name: Optional[str] = None) -> "ExperimentTracker":
        """Create a new instance or return the existing one.
        
        Args:
            mlflow_config: Configuration for MLflow tracking
            exp_name: Optional experiment name. If provided, sets the experiment name before initialization.
            
        Returns:
            The singleton instance of ExperimentTracker
        """
        if cls._instance is None:
            cls._instance = super(ExperimentTracker, cls).__new__(cls)
            cls._instance._initialized = False
        
        # Set experiment name before initialization if provided
        if exp_name is not None:
            cls._instance._exp_name = exp_name
        
        if mlflow_config is not None and not cls._instance._initialized:
            cls._instance.initialize(mlflow_config)
        
        return cls._instance
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Empty init to allow instance creation without arguments."""
        pass
    
    def initialize(self, mlflow_config: MLflowConfig) -> None:
        """Initialize the experiment tracker with configuration settings.
        
        Args:
            mlflow_config: Configuration for MLflow tracking
        """
        if self._initialized:
            return
        
        self._initialized = True
        self._config = mlflow_config
        
        if not mlflow_config.enabled:
            logger.debug("MLflow tracking is disabled")
            return
        
        if not mlflow_config.server_url:
            logger.warning("MLflow server URL not provided, tracking disabled")
            return
        
        self._has_errors = False
        self._configure_mlflow_params(mlflow_config)
        self._initialize_mlflow_experiment()
        self._setup_executor()
    
    @property
    def _should_log_to_mlflow(self) -> bool:
        """Check if MLflow logging should be enabled."""
        return (
            self._initialized
            and self._config is not None
            and self._config.enabled
            and self._mlflow_server is not None
        )
    
    @property
    def exp_name(self) -> str:
        """Get experiment name."""
        if not hasattr(self, "_exp_name") or self._exp_name is None:
            return "temp_exp"
        return self._exp_name
    
    @exp_name.setter
    def exp_name(self, value: str) -> None:
        """Set experiment name."""
        self._exp_name = value
    
    @property
    def active_run(self) -> Optional[mlflow.ActiveRun]:
        """Get active MLflow run."""
        return self._active_run
    
    @property
    def has_errors(self) -> bool:
        """Check if there were any errors during tracking."""
        return self._has_errors
    
    @has_errors.setter
    def has_errors(self, value: bool) -> None:
        """Set error flag."""
        self._has_errors = value
    
    def log_metrics(self, metrics: dict[str, float], step: Optional[int] = None) -> None:
        """Log metrics to MLflow synchronously.
        
        Args:
            metrics: Dictionary of metric names to values
            step: Optional step number for the metrics
        """
        if not self._should_log_to_mlflow or not self._active_run:
            return
        
        try:
            if step is not None:
                mlflow.log_metrics(metrics, step=step)
            else:
                for key, value in metrics.items():
                    mlflow.log_metric(key, value)
        except Exception as e:
            self._has_errors = True
            logger.error(f"Failed to log metrics: {e}")
    
    def log_params(self, params: dict[str, Any]) -> None:
        """Log parameters to MLflow.
        
        Args:
            params: Dictionary of parameter names to values
        """
        if not self._should_log_to_mlflow or not self._active_run:
            return
        
        try:
            for key, value in params.items():
                # Convert complex types to strings
                if isinstance(value, (list, dict)):
                    mlflow.log_param(key, str(value))
                elif value is not None:
                    mlflow.log_param(key, value)
        except Exception as e:
            self._has_errors = True
            logger.error(f"Failed to log parameters: {e}")
    
    def log_rendered_images(
        self,
        paths: Any,  # PathCofig type
        sides: list[str]
    ) -> None:
        """Log rendered images to MLflow.
        
        Args:
            paths: PathCofig object containing render paths
            sides: List of camera sides that were rendered (e.g., ['front', 'back', 'straight-front', 'straight-back'])
        """
        if not self._should_log_to_mlflow or not self._active_run:
            return
        
        if self._local_artifact_dir is None:
            return
        
        try:
            # Create local directory for artifacts
            local_dir = Path(self._local_artifact_dir) / self._exp_name / "renders"
            local_dir.mkdir(parents=True, exist_ok=True)
            
            for side in sides:
                render_path = paths.render_path(side)
                if not render_path.exists():
                    logger.warning(f"Render image not found: {render_path}")
                    continue
                
                # Copy to local artifact directory
                local_img_path = local_dir / f"render_{side}.png"
                shutil.copy2(render_path, local_img_path)
                
                # Log to MLflow asynchronously
                if self._executor is not None:
                    future = self._executor.submit(
                        self._sync_to_remote_wrapper,
                        str(local_img_path),
                        "renders",
                        f"render_{side}"
                    )
                    self._pending_tasks.append(future)
                else:
                    # Fallback to synchronous
                    self._sync_to_remote_wrapper(
                        str(local_img_path),
                        "renders",
                        f"render_{side}"
                    )
        
        except Exception as e:
            self._has_errors = True
            error_stack = traceback.format_exc()
            logger.error(f"Failed to log rendered images: {e}")
            logger.error(f"Stack trace:\n{error_stack}")
    
    def log_texture(
        self,
        paths: Any,  # PathCofig type
    ) -> None:
        """Log texture.png file to MLflow.
        
        Args:
            paths: PathCofig object containing texture path (paths.g_texture)
        """
        if not self._should_log_to_mlflow or not self._active_run:
            return
        
        if self._local_artifact_dir is None:
            return
        
        try:
            # Check if texture file exists
            texture_path = paths.g_texture
            if not texture_path.exists():
                logger.warning(f"Texture file not found: {texture_path}")
                return
            
            # Create local directory for artifacts
            local_dir = Path(self._local_artifact_dir) / self._exp_name / "textures"
            local_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy to local artifact directory
            local_texture_path = local_dir / "texture.png"
            shutil.copy2(texture_path, local_texture_path)
            
            # Log to MLflow asynchronously
            if self._executor is not None:
                future = self._executor.submit(
                    self._sync_to_remote_wrapper,
                    str(local_texture_path),
                    "textures",
                    "texture"
                )
                self._pending_tasks.append(future)
            else:
                # Fallback to synchronous
                self._sync_to_remote_wrapper(
                    str(local_texture_path),
                    "textures",
                    "texture"
                )
        
        except Exception as e:
            self._has_errors = True
            error_stack = traceback.format_exc()
            logger.error(f"Failed to log texture file: {e}")
            logger.error(f"Stack trace:\n{error_stack}")
    
    def end_run(self) -> None:
        """End the MLflow run and clean up resources."""
        if not self._initialized:
            return
        
        # Wait for pending tasks
        if hasattr(self, "_pending_tasks") and self._pending_tasks:
            logger.info(f"Waiting for {len(self._pending_tasks)} pending tasks to complete...")
            concurrent.futures.wait(self._pending_tasks)
            logger.info("All pending tasks completed")
        
        if self._should_log_to_mlflow:
            if hasattr(self, "_active_run") and self._active_run:
                # Mark the run as failed if there were any errors
                if self._has_errors:
                    logger.warning("Marking experiment as failed due to errors during execution")
                    mlflow.end_run(status="FAILED")
                else:
                    mlflow.end_run(status="FINISHED")
                
                self._active_run = None
        
        # Shutdown the executor
        if hasattr(self, "_executor") and self._executor:
            try:
                current_thread = threading.current_thread()
                is_current_thread = any(
                    getattr(worker, "_thread", None) is current_thread
                    for worker in self._executor._threads
                )
                self._executor.shutdown(wait=not is_current_thread)
            except RuntimeError as e:
                self._has_errors = True
                error_stack = traceback.format_exc()
                logger.error(f"Error shutting down executor: {e}")
                logger.error(f"Stack trace:\n{error_stack}")
        
        # Clean up temp directory
        if self._temp_artifact_dir and os.path.exists(self._temp_artifact_dir):
            try:
                shutil.rmtree(self._temp_artifact_dir)
            except Exception as e:
                self._has_errors = True
                error_stack = traceback.format_exc()
                logger.error(f"Failed to clean up temporary directory: {e}")
                logger.error(f"Stack trace:\n{error_stack}")
        
        logger.info("MLflow run ended successfully")
        
        # Reset singleton state for next experiment (useful for grid simulations)
        # This allows creating a new tracker instance for the next simulation
        if hasattr(self, "_initialized"):
            self._initialized = False
        # Note: We don't reset _instance to None here to maintain singleton pattern
        # If you need a completely fresh instance, you can reset cls._instance = None externally
    
    def _configure_mlflow_params(self, mlflow_config: MLflowConfig) -> None:
        """Configure MLflow parameters from config."""
        self._remote_server_alias = mlflow_config.remote_server_alias
        self._mlflow_server = mlflow_config.server_url
        self._local_artifact_dir = mlflow_config.local_artifact_dir
        self._remote_artifact_uri = mlflow_config.remote_artifact_uri
        self._remote_mlflow_path = mlflow_config.remote_mlflow_path
        self._max_workers = mlflow_config.max_workers
        self._temp_artifact_dir = tempfile.mkdtemp()
        os.environ["MLFLOW_ARTIFACT_ROOT"] = self._temp_artifact_dir
    
    def _initialize_mlflow_experiment(self) -> None:
        """Initialize MLflow experiment and start a run."""
        if not self._should_log_to_mlflow or not self._mlflow_server:
            logger.warning("MLflow server not set or logging disabled, skipping experiment creation")
            return
        
        mlflow.set_tracking_uri(uri=self._mlflow_server)
        
        # Try to create or get existing experiment
        try:
            self._experiment_id = mlflow.create_experiment(self._exp_name)
            logger.info(f"Created new experiment: {self._exp_name}")
        except Exception as e:
            self._handle_existing_experiment(e)
        
        # Start the run
        self._active_run = mlflow.start_run(
            run_name=self._exp_name,
            experiment_id=self._experiment_id
        )
        logger.info(f"Started MLflow run: {self._exp_name}")
    
    def _handle_existing_experiment(self, exception: Exception) -> None:
        """Handle case when experiment already exists.
        
        Args:
            exception: The exception that was raised when trying to create the experiment
        """
        error_str = str(exception)
        if "RESOURCE_ALREADY_EXISTS" in error_str or "UNIQUE constraint failed" in error_str:
            try:
                experiment = mlflow.get_experiment_by_name(self._exp_name)
                if experiment is None:
                    mlflow.delete_experiment(self._exp_name)
                    self._experiment_id = mlflow.create_experiment(self._exp_name)
                    logger.info(f"Recreated experiment after cleanup: {self._exp_name}")
                elif experiment.lifecycle_stage == "deleted":
                    mlflow.delete_experiment(experiment.experiment_id)
                    self._experiment_id = mlflow.create_experiment(self._exp_name)
                    logger.info(f"Recreated experiment: {self._exp_name}")
                else:
                    self._experiment_id = experiment.experiment_id
                    logger.info(f"Using existing experiment: {self._exp_name}")
            except Exception as e:
                logger.error(f"Error handling existing experiment: {e}")
                unique_name = f"{self._exp_name}_{int(time.time())}"
                self._experiment_id = mlflow.create_experiment(unique_name)
                self._exp_name = unique_name
                logger.info(f"Created new experiment with unique name: {unique_name}")
        else:
            raise exception
    
    def _setup_executor(self) -> None:
        """Set up thread pool executor for async operations."""
        if self._should_log_to_mlflow and self._mlflow_server:
            self._client = MlflowClient()
        
        # Initialize thread pool executor for async operations
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers)
        logger.info(f"Initialized MLflow thread pool executor with {self._max_workers} workers")
        self._pending_tasks: list[concurrent.futures.Future[Any]] = []
    
    async def _async_sync_to_remote(
        self, local_img_path: str, subfolder_name: str, filename: str
    ) -> None:
        """Asynchronously sync an image to the remote server and log it to MLflow.
        
        Args:
            local_img_path: Path to the local image file
            subfolder_name: Name of the subfolder to store the image in
            filename: Name of the image file without extension
        """
        try:
            remote_base = f"{self._remote_artifact_uri}/{self._exp_name}"
            remote_folder = f"{remote_base}/{subfolder_name}"
            
            run_id = (
                self._active_run.info.run_id
                if self._active_run and self._active_run.info
                else None
            )
            
            if self._remote_server_alias is None:
                # Local mode - just copy the file to the destination
                os.makedirs(remote_folder, exist_ok=True)
                full_remote_path = f"{remote_folder}/{filename}.png"
                shutil.copy2(local_img_path, full_remote_path)
                
                # Use MLflow CLI for local mode
                mlflow_cmd = (
                    f"mlflow artifacts log-artifact --run-id {run_id} "
                    f"--artifact-path {subfolder_name} --local-file {full_remote_path}"
                )
                
                process = await asyncio.create_subprocess_shell(
                    mlflow_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await process.communicate()
                
                if stderr:
                    logger.debug(f"Local MLflow CLI: {stderr.decode()}")
                
                if process.returncode != 0:
                    logger.warning("Failed to log artifact via local MLflow CLI. Using fallback method.")
                    mlflow.log_artifact(local_path=full_remote_path, artifact_path=subfolder_name)
            else:
                remote_dir = f"{self._remote_server_alias}:{remote_folder}"
                mkdir_cmd = ["ssh", self._remote_server_alias, f"mkdir -p {remote_folder}"]
                process = await asyncio.create_subprocess_exec(
                    *mkdir_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                # Use scp to copy the file to the remote server
                scp_cmd = ["scp", local_img_path, f"{remote_dir}/"]
                process = await asyncio.create_subprocess_exec(
                    *scp_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                full_remote_path = f"{remote_folder}/{filename}.png"
                
                mlflow_cmd = f"""
                ssh {self._remote_server_alias} 'MLFLOW_TRACKING_URI={self._mlflow_server} \
                {self._remote_mlflow_path} artifacts log-artifact --run-id {run_id} \
                --artifact-path {subfolder_name} \
                --local-file {full_remote_path}'
                """
                
                process = await asyncio.create_subprocess_shell(
                    mlflow_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await process.communicate()
                
                if stderr:
                    logger.debug(f"MLflow CLI: {stderr.decode()}")
        
        except Exception as e:
            logger.warning(f"Failed to sync artifact to server: {e}")
    
    def _sync_to_remote_wrapper(
        self, local_img_path: str, subfolder_name: str, filename: str
    ) -> None:
        """Wrapper to run the async function in the executor.
        
        Args:
            local_img_path: Path to the local image file
            subfolder_name: Name of the subfolder to store the image in
            filename: Name of the image file without extension
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self._async_sync_to_remote(local_img_path, subfolder_name, filename)
            )
        finally:
            loop.close()
    
    def __del__(self) -> None:
        """Clean up when object is destroyed."""
        if hasattr(self, "_pending_tasks") and self._pending_tasks:
            concurrent.futures.wait(self._pending_tasks)
        
        if hasattr(self, "_executor") and self._executor:
            try:
                current_thread = threading.current_thread()
                is_current_thread = any(
                    getattr(worker, "_thread", None) is current_thread
                    for worker in self._executor._threads
                )
                self._executor.shutdown(wait=not is_current_thread)
            except RuntimeError:
                pass
        
        if hasattr(self, "_active_run") and self._active_run:
            self.end_run()
        
        if self._temp_artifact_dir and os.path.exists(self._temp_artifact_dir):
            try:
                shutil.rmtree(self._temp_artifact_dir)
            except Exception as e:
                logger.debug(f"Failed to clean up temporary directory: {e}")

