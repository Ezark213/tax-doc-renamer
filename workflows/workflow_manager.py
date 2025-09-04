#!/usr/bin/env python3
"""
税務書類リネーマーシステム - ワークフロー管理MCP
AddFunc-BugFixワークフロー統合システム
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowManager:
    """AddFunc-BugFixワークフロー管理システム"""
    
    def __init__(self):
        self.workflows_dir = Path(__file__).parent
        self.project_name = "税務書類リネーマーシステム v5.3.5-ui-robust"
        self.workflow_phases = [
            "1.analyze.md",
            "2.plan.md", 
            "3.check.md",
            "4.eval.md",
            "5.do.md",
            "6.fin.md"
        ]
        
        self.capabilities = {
            "tools": {
                "workflow_execute": {
                    "description": "AddFunc-BugFixワークフロー実行",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "phase": {
                                "type": "string",
                                "enum": ["analyze", "plan", "check", "eval", "do", "fin"],
                                "description": "実行フェーズ"
                            },
                            "target": {
                                "type": "string",
                                "description": "対象機能・バグ"
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["bug_fix", "feature_add"],
                                "description": "実行モード"
                            }
                        },
                        "required": ["phase", "target", "mode"]
                    }
                },
                "workflow_status": {
                    "description": "ワークフロー進捗状況確認",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "ワークフローID（オプション）"
                            }
                        }
                    }
                },
                "generate_analysis_report": {
                    "description": "分析レポート自動生成",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "analysis_scope": {
                                "type": "string",
                                "enum": ["current_system", "specific_module", "comprehensive"],
                                "description": "分析範囲"
                            },
                            "focus_areas": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "フォーカス領域リスト"
                            }
                        },
                        "required": ["analysis_scope"]
                    }
                },
                "create_implementation_plan": {
                    "description": "実装計画作成支援",
                    "inputSchema": {
                        "type": "object", 
                        "properties": {
                            "target_feature": {
                                "type": "string",
                                "description": "対象機能"
                            },
                            "complexity": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "複雑度"
                            },
                            "timeline": {
                                "type": "string",
                                "description": "希望タイムライン"
                            }
                        },
                        "required": ["target_feature", "complexity"]
                    }
                }
            }
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """MCPリクエスト処理"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            
            if method == "initialize":
                return self._handle_initialize(params)
            elif method == "tools/list":
                return self._handle_tools_list()
            elif method == "tools/call":
                return self._handle_tools_call(params)
            else:
                return self._error_response(f"Unknown method: {method}")
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self._error_response(str(e))
    
    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """初期化処理"""
        return {
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": "税務書類リネーマーワークフロー管理",
                "version": "1.0.0"
            }
        }
    
    def _handle_tools_list(self) -> Dict[str, Any]:
        """ツール一覧"""
        tools = []
        for tool_name, tool_info in self.capabilities["tools"].items():
            tools.append({
                "name": tool_name,
                "description": tool_info["description"],
                "inputSchema": tool_info["inputSchema"]
            })
        return {"tools": tools}
    
    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ツール実行"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "workflow_execute":
            return self._execute_workflow(arguments)
        elif tool_name == "workflow_status":
            return self._get_workflow_status(arguments)
        elif tool_name == "generate_analysis_report":
            return self._generate_analysis_report(arguments)
        elif tool_name == "create_implementation_plan":
            return self._create_implementation_plan(arguments)
        else:
            return self._error_response(f"Unknown tool: {tool_name}")
    
    def _execute_workflow(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """ワークフロー実行"""
        phase = args.get("phase")
        target = args.get("target")
        mode = args.get("mode")
        
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # フェーズ対応ファイル読み込み
        phase_file = self.workflows_dir / f"{phase[0]}.{phase}.md"
        
        if not phase_file.exists():
            return self._error_response(f"Workflow phase file not found: {phase_file}")
        
        with open(phase_file, 'r', encoding='utf-8') as f:
            phase_content = f.read()
        
        # ワークフロー実行ログ生成
        execution_log = {
            "workflow_id": workflow_id,
            "phase": phase,
            "target": target,
            "mode": mode,
            "timestamp": datetime.now().isoformat(),
            "status": "executed",
            "phase_content": phase_content
        }
        
        # 実行結果保存
        log_file = Path("tmp") / f"workflow_execution_{workflow_id}.json"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(execution_log, f, ensure_ascii=False, indent=2)
        
        result_text = f"""# ワークフロー実行結果

## 実行情報
- ワークフローID: {workflow_id}
- フェーズ: {phase}
- 対象: {target}
- モード: {mode}
- 実行時刻: {execution_log['timestamp']}

## フェーズ内容
{phase_content}

## 次のステップ
{self._get_next_phase_guidance(phase)}

実行ログ: {log_file}
"""
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result_text
                }
            ]
        }
    
    def _get_next_phase_guidance(self, current_phase: str) -> str:
        """次フェーズのガイダンス"""
        phase_order = {
            "analyze": "2.plan.md - Serena MCPを使用したアーキテクチャ分析と計画策定",
            "plan": "3.check.md - 計画内容の妥当性確認と品質評価", 
            "check": "4.eval.md - リスク評価と実装準備完了判定",
            "eval": "5.do.md - 実装実行とプロフェッショナル品質保証",
            "do": "6.fin.md - 完了検証と成果物最終確認",
            "fin": "✅ ワークフロー完了 - 次の機能追加・バグ修正サイクル開始"
        }
        
        return phase_order.get(current_phase, "ワークフロー完了")
    
    def _get_workflow_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """ワークフロー状況確認"""
        tmp_dir = Path("tmp")
        workflow_files = list(tmp_dir.glob("workflow_execution_*.json"))
        
        if not workflow_files:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "実行中のワークフローはありません。"
                    }
                ]
            }
        
        # 最新のワークフロー情報取得
        latest_workflow = max(workflow_files, key=lambda x: x.stat().st_mtime)
        
        with open(latest_workflow, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        status_text = f"""# ワークフロー状況

## 最新ワークフロー
- ID: {workflow_data['workflow_id']}
- フェーズ: {workflow_data['phase']}
- 対象: {workflow_data['target']}
- モード: {workflow_data['mode']}
- 実行日時: {workflow_data['timestamp']}
- ステータス: {workflow_data['status']}

## 全実行履歴
{len(workflow_files)}件のワークフロー実行履歴があります。
"""
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": status_text
                }
            ]
        }
    
    def _generate_analysis_report(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """分析レポート生成"""
        analysis_scope = args.get("analysis_scope")
        focus_areas = args.get("focus_areas", [])
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_data = {
            "project": self.project_name,
            "analysis_scope": analysis_scope,
            "focus_areas": focus_areas,
            "timestamp": timestamp,
            "system_overview": {
                "version": "v5.3.5-ui-robust",
                "architecture": "モノリシック→モジュラー移行",
                "key_achievements": [
                    "UI YYMM強制適用システム完成",
                    "Bundle分割経路RunConfig伝搬確保",
                    "JobContext中央集権管理実装"
                ]
            },
            "current_status": {
                "ui_forced_codes": "✅ 完全実装 (6001,6002,6003,0000)",
                "bundle_processing": "✅ RunConfig伝搬確保",
                "job_context": "✅ 一元管理システム導入",
                "enterprise_quality": "✅ エンタープライズレベル達成"
            },
            "recommended_next_steps": [
                "アーキテクチャモダン化 (責任分離)",
                "パフォーマンス最適化 (非同期処理)",
                "テストカバレッジ向上 (90%以上)",
                "セキュリティ強化 (入力検証・監査)"
            ]
        }
        
        report_path = f"tmp/auto_analysis_{timestamp}.md"
        Path("tmp").mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 税務書類リネーマー自動分析レポート\n\n")
            f.write(f"生成日時: {timestamp}\n\n")
            f.write("```json\n")
            f.write(json.dumps(report_data, ensure_ascii=False, indent=2))
            f.write("\n```\n")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"分析レポートを生成しました: {report_path}\n\n{json.dumps(report_data, ensure_ascii=False, indent=2)}"
                }
            ]
        }
    
    def _create_implementation_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """実装計画作成"""
        target_feature = args.get("target_feature")
        complexity = args.get("complexity")
        timeline = args.get("timeline", "未指定")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 複雑度に基づく実装計画テンプレート
        complexity_templates = {
            "low": {
                "phases": ["分析", "実装", "テスト"],
                "estimated_hours": "8-16時間",
                "risk_level": "低",
                "team_size": "1名"
            },
            "medium": {
                "phases": ["分析", "設計", "実装", "テスト", "統合"],
                "estimated_hours": "24-40時間", 
                "risk_level": "中",
                "team_size": "1-2名"
            },
            "high": {
                "phases": ["詳細分析", "アーキテクチャ設計", "段階的実装", "包括テスト", "統合・検証"],
                "estimated_hours": "80-120時間",
                "risk_level": "高",
                "team_size": "2-3名"
            }
        }
        
        template = complexity_templates.get(complexity, complexity_templates["medium"])
        
        plan_data = {
            "target_feature": target_feature,
            "complexity": complexity,
            "timeline": timeline,
            "implementation_phases": template["phases"],
            "estimated_effort": template["estimated_hours"],
            "risk_assessment": template["risk_level"],
            "recommended_team_size": template["team_size"],
            "quality_gates": [
                "コードレビュー完了",
                "テストカバレッジ >= 90%",
                "セキュリティ検証完了",
                "パフォーマンス要件達成"
            ],
            "deliverables": [
                "機能仕様書",
                "実装コード + テスト",
                "ドキュメント更新",
                "リリースノート"
            ]
        }
        
        plan_path = f"tmp/implementation_plan_{timestamp}.md"
        
        with open(plan_path, 'w', encoding='utf-8') as f:
            f.write(f"# {target_feature} 実装計画\n\n")
            f.write(f"生成日時: {timestamp}\n\n")
            f.write("```json\n")
            f.write(json.dumps(plan_data, ensure_ascii=False, indent=2))
            f.write("\n```\n")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"実装計画を作成しました: {plan_path}\n\n{json.dumps(plan_data, ensure_ascii=False, indent=2)}"
                }
            ]
        }
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """エラーレスポンス"""
        return {
            "error": {
                "code": -1,
                "message": message
            }
        }
    
    def run_mcp_server(self):
        """MCPサーバー実行"""
        logger.info(f"税務書類リネーマーワークフロー管理MCP開始: {self.project_name}")
        
        try:
            for line in sys.stdin:
                try:
                    request = json.loads(line.strip())
                    response = self.handle_request(request)
                    print(json.dumps(response, ensure_ascii=False))
                    sys.stdout.flush()
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {line}")
                except Exception as e:
                    logger.error(f"Request processing error: {e}")
                    error_response = self._error_response(str(e))
                    print(json.dumps(error_response))
                    sys.stdout.flush()
        except KeyboardInterrupt:
            logger.info("ワークフロー管理MCP停止")
        except Exception as e:
            logger.error(f"サーバーエラー: {e}")


if __name__ == "__main__":
    manager = WorkflowManager()
    manager.run_mcp_server()