from .base import Collector, CollectorError
from .github import GitHubCollector
from .web import WebCollector

__all__ = ["Collector", "CollectorError", "GitHubCollector", "WebCollector"]
