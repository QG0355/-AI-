import json
import os
import re
import logging
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tickets_api.models import AiSetting, Ticket
from tickets_api.simple_sync import sync_ticket as sync_ticket_simple


class Command(BaseCommand):
    help = "AI 自动过审：扫描 pending_dorm 工单，判断标题/类别/描述是否匹配，匹配则自动通过并打标"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200)
        parser.add_argument("--force", action="store_true", default=False)
        parser.add_argument("--dry-run", action="store_true", default=False)
        parser.add_argument("--reject-on-mismatch", action="store_true", default=False)
        parser.add_argument("--loop", action="store_true", default=False)
        parser.add_argument("--interval", type=int, default=20)

    def handle(self, *args, **options):
        cfg = self._load_ai_config()
        if not cfg.get("enabled", True):
            self.stdout.write(self.style.WARNING("AI 助手已在后台关闭，跳过 ai_auto_review"))
            return

        loop = bool(options.get("loop"))
        interval = int(options.get("interval") or 20)
        if interval < 1:
            interval = 1

        while True:
            self._run_once(cfg, options)
            if not loop:
                break
            time.sleep(interval)

    def _run_once(self, cfg: dict, options: dict):
        limit = int(options.get("limit") or 200)
        force = bool(options.get("force"))
        dry_run = bool(options.get("dry_run"))
        reject_on_mismatch = bool(options.get("reject_on_mismatch"))

        qs = Ticket.objects.filter(status="pending_dorm").order_by("submitTime", "id")
        if not force:
            qs = qs.filter(ai_auto_checked_at__isnull=True)
        qs = qs[:limit]

        total = 0
        approved = 0
        rejected = 0
        skipped = 0

        for t in qs.iterator():
            total += 1
            try:
                res = self._ai_review_ticket(t, cfg)
            except Exception:
                logging.getLogger(__name__).warning("ai_auto_review_ticket_failed", exc_info=True)
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"ticket={t.id} match={bool(res.get('match'))} suggested_category={res.get('suggested_category') or ''}"
                )
                continue

            now = timezone.now()
            with transaction.atomic():
                t = Ticket.objects.select_for_update().get(id=t.id)
                if t.status != "pending_dorm":
                    skipped += 1
                    continue

                t.ai_auto_checked_at = now
                t.ai_suggested_category = (res.get("suggested_category") or "").strip()[:50]
                t.ai_auto_reason = (res.get("reason") or "").strip()

                if bool(res.get("match")):
                    t.ai_auto_approved = True
                    t.status = "pending_dispatch"
                    t.rejected_reason = None
                    t.auditor = None
                    t.save(
                        update_fields=[
                            "ai_auto_checked_at",
                            "ai_suggested_category",
                            "ai_auto_reason",
                            "ai_auto_approved",
                            "status",
                            "rejected_reason",
                            "auditor",
                            "updateTime",
                        ]
                    )
                    approved += 1
                else:
                    t.ai_auto_approved = False
                    if reject_on_mismatch:
                        t.status = "rejected"
                        t.rejected_reason = (t.ai_auto_reason or "")[:1000] or "AI 自动审核未通过"
                        t.auditor = None
                        t.save(
                            update_fields=[
                                "ai_auto_checked_at",
                                "ai_suggested_category",
                                "ai_auto_reason",
                                "ai_auto_approved",
                                "status",
                                "rejected_reason",
                                "auditor",
                                "updateTime",
                            ]
                        )
                        rejected += 1
                    else:
                        t.save(
                            update_fields=[
                                "ai_auto_checked_at",
                                "ai_suggested_category",
                                "ai_auto_reason",
                                "ai_auto_approved",
                                "updateTime",
                            ]
                        )

                try:
                    sync_ticket_simple(t)
                except Exception:
                    pass

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"ai_auto_review dry-run 完成，共扫描 {total} 条"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"ai_auto_review 完成：扫描 {total} 条，通过 {approved} 条，驳回 {rejected} 条，跳过 {skipped} 条"
                )
            )

    def _mask_pii(self, text: str) -> str:
        text = re.sub(r"\b1\d{10}\b", "[已脱敏手机号]", text or "")
        text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[已脱敏邮箱]", text)
        text = re.sub(r"\b\d{6,}\b", "[已脱敏数字]", text)
        text = re.sub(r"[A-Za-z0-9_\-]{24,}", "[已脱敏标识]", text)
        return text

    def _load_ai_config(self) -> dict:
        api_key = os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        base_url = (os.environ.get("AI_BASE_URL") or "https://api.deepseek.com/v1").strip().rstrip("/")
        model = (os.environ.get("AI_MODEL") or "deepseek-chat").strip()
        try:
            timeout = float(os.environ.get("AI_TIMEOUT") or 30)
        except Exception:
            timeout = 30.0

        enabled = True
        s = AiSetting.objects.order_by("-updated_at", "-id").first()
        if s:
            enabled = bool(getattr(s, "enabled", True))
            if (s.api_base_url or "").strip():
                base_url = s.api_base_url.strip().rstrip("/")
            if (s.api_model or "").strip():
                model = s.api_model.strip()
            if (s.api_key or "").strip():
                api_key = s.api_key.strip()
            if getattr(s, "timeout_seconds", None):
                try:
                    timeout = float(s.timeout_seconds)
                except Exception:
                    pass

        return {
            "enabled": enabled,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "timeout": timeout,
        }

    def _ai_review_ticket(self, ticket: Ticket, cfg: dict) -> dict:
        title = (getattr(ticket, "title", "") or "").strip()
        category = (getattr(ticket, "category", "") or "").strip()
        description = (getattr(ticket, "description", "") or "").strip()

        categories = [c[0] for c in getattr(Ticket, "CATEGORY_CHOICES", [])] or []
        safe_title = self._mask_pii(title)
        safe_desc = self._mask_pii(description)

        if not cfg.get("api_key") or not str(cfg.get("base_url") or "").startswith("https://"):
            return self._rule_review_ticket(safe_title, category, safe_desc, categories)

        system_prompt = (
            "你是校园报修工单“审核”助手。你的任务：判断“标题/报修类别/故障描述”三者是否一致。"
            "你必须只输出 JSON，不要输出其他文字。\n\n"
            "输出 JSON 结构："
            '{"match": true/false, "suggested_category": "类别", "reason": "原因(简短)"}\n\n'
            f"可选类别列表：{json.dumps(categories, ensure_ascii=False)}\n"
            "match=true 的标准：标题能概括描述的核心问题，且类别与描述相符；出现明显错类/牛头不对马嘴则 match=false。"
        )
        user_content = json.dumps(
            {"title": safe_title, "category": category, "description": safe_desc}, ensure_ascii=False
        )
        payload = {
            "model": cfg.get("model"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0,
        }

        logger = logging.getLogger(__name__)
        try:
            req = Request(
                f"{cfg.get('base_url')}/chat/completions",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {cfg.get('api_key')}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(req, timeout=float(cfg.get("timeout") or 30)) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            msg = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            parsed = self._parse_json_from_text(msg)
            if parsed:
                return {
                    "match": bool(parsed.get("match")),
                    "suggested_category": (parsed.get("suggested_category") or "").strip(),
                    "reason": (parsed.get("reason") or "").strip()[:2000],
                }
        except HTTPError:
            logger.warning("ai_auto_review_http_error", exc_info=True)
        except URLError:
            logger.warning("ai_auto_review_url_error", exc_info=True)
        except Exception:
            logger.warning("ai_auto_review_error", exc_info=True)

        return self._rule_review_ticket(safe_title, category, safe_desc, categories)

    def _parse_json_from_text(self, text: str):
        if not text:
            return None
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None

    def _rule_review_ticket(self, title: str, category: str, description: str, categories: list) -> dict:
        normalized = (title + "\n" + description).lower()
        suggested = "其他"
        if any(k in normalized for k in ["wifi", "wi-fi", "网络", "上网", "断网", "路由", "宽带"]):
            suggested = "网络连接"
        elif any(k in normalized for k in ["水", "漏水", "水龙头", "下水", "电", "灯", "跳闸", "插座", "电闸", "开关"]):
            suggested = "水电问题"
        elif any(k in normalized for k in ["空调", "冰箱", "洗衣机", "热水器", "风扇", "设备", "电器"]):
            suggested = "设备故障"
        elif any(k in normalized for k in ["柜", "衣柜", "桌", "椅", "床"]):
            suggested = "柜子损坏"
        elif any(k in normalized for k in ["门", "窗", "锁", "玻璃"]):
            suggested = "门窗损坏"

        if categories and suggested not in categories:
            suggested = categories[-1]

        is_match = bool(category) and (category == suggested or category == "其他")
        reason = f"规则审核：建议类别={suggested}，当前类别={category or ''}。"
        return {"match": is_match, "suggested_category": suggested, "reason": reason}
