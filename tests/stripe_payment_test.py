"""
Stripe決済テストツール
tests/stripe_payment_test.py

Stripe決済機能の包括的なテストスイート
"""
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import unittest
from unittest.mock import Mock, patch, MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.payment_service import PaymentService, PaymentUI
from config.unified_config import UnifiedConfig


@dataclass
class StripeTestResult:
    """Stripeテスト結果"""
    test_name: str
    success: bool
    message: str
    duration: float
    details: Dict[str, Any] = None


class StripePaymentTester:
    """Stripe決済テスタークラス"""
    
    def __init__(self):
        self.test_results: List[StripeTestResult] = []
        self.stripe_available = self._check_stripe_sdk()
        self.test_env_configured = self._check_test_environment()
        
    def _check_stripe_sdk(self) -> bool:
        """Stripe SDKの利用可能性をチェック"""
        try:
            import stripe
            return True
        except ImportError:
            return False
    
    def _check_test_environment(self) -> bool:
        """テスト環境の設定をチェック"""
        secret_key = os.getenv('STRIPE_SECRET_KEY', '')
        pub_key = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
        
        return (secret_key.startswith('sk_test_') and 
                pub_key.startswith('pk_test_'))
    
    def run_all_tests(self) -> Dict[str, Any]:
        """全てのStripeテストを実行"""
        print("🔄 Stripe決済テスト開始")
        print("=" * 50)
        
        # 事前チェック
        if not self.stripe_available:
            print("❌ Stripe SDKが利用できません")
            print("   pip install stripe を実行してください")
            return self._generate_summary()
        
        if not self.test_env_configured:
            print("⚠️  テスト環境が正しく設定されていません")
            print("   STRIPE_SECRET_KEY と STRIPE_PUBLISHABLE_KEY を確認してください")
        
        # テスト実行
        test_methods = [
            ("SDK初期化テスト", self.test_stripe_sdk_initialization),
            ("PaymentService初期化テスト", self.test_payment_service_initialization),
            ("顧客作成テスト", self.test_customer_creation),
            ("PaymentMethod作成テスト", self.test_payment_method_creation),
            ("価格作成テスト", self.test_price_creation),
            ("サブスクリプション作成テスト", self.test_subscription_creation),
            ("サブスクリプション更新テスト", self.test_subscription_update),
            ("サブスクリプションキャンセルテスト", self.test_subscription_cancellation),
            ("請求書取得テスト", self.test_invoice_retrieval),
            ("エラーハンドリングテスト", self.test_error_handling),
            ("決済UI表示テスト", self.test_payment_ui_display)
        ]
        
        for test_name, test_method in test_methods:
            print(f"\n🧪 {test_name}")
            start_time = datetime.now()
            
            try:
                result = test_method()
                duration = (datetime.now() - start_time).total_seconds()
                
                if result.get("success", False):
                    print(f"   ✅ 成功: {result.get('message', '')}")
                    self.test_results.append(StripeTestResult(
                        test_name=test_name,
                        success=True,
                        message=result.get('message', ''),
                        duration=duration,
                        details=result.get('details', {})
                    ))
                else:
                    print(f"   ❌ 失敗: {result.get('message', '')}")
                    self.test_results.append(StripeTestResult(
                        test_name=test_name,
                        success=False,
                        message=result.get('message', ''),
                        duration=duration,
                        details=result.get('details', {})
                    ))
                    
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                print(f"   ❌ 例外: {str(e)}")
                self.test_results.append(StripeTestResult(
                    test_name=test_name,
                    success=False,
                    message=f"例外が発生: {str(e)}",
                    duration=duration
                ))
        
        return self._generate_summary()
    
    def test_stripe_sdk_initialization(self) -> Dict[str, Any]:
        """Stripe SDKの初期化テスト"""
        if not self.stripe_available:
            return {"success": False, "message": "Stripe SDKが利用できません"}
        
        try:
            import stripe
            
            # API キーの設定確認
            original_key = stripe.api_key
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            
            if not stripe.api_key:
                return {"success": False, "message": "STRIPE_SECRET_KEYが設定されていません"}
            
            # 簡単なAPI呼び出しテスト（残高取得）
            if self.test_env_configured:
                try:
                    balance = stripe.Balance.retrieve()
                    return {
                        "success": True,
                        "message": f"API接続成功",
                        "details": {
                            "available_balance": balance.available,
                            "pending_balance": balance.pending
                        }
                    }
                except Exception as api_error:
                    return {
                        "success": False,
                        "message": f"API呼び出しエラー: {str(api_error)}",
                        "details": {"api_error": str(api_error)}
                    }
            else:
                return {
                    "success": True,
                    "message": "SDK初期化成功（テスト環境未設定）"
                }
                
        except Exception as e:
            return {"success": False, "message": f"SDK初期化エラー: {str(e)}"}
    
    def test_payment_service_initialization(self) -> Dict[str, Any]:
        """PaymentService初期化テスト"""
        try:
            if not self.stripe_available:
                # Stripe SDKなしでの初期化テスト
                service = PaymentService()
                return {"success": True, "message": "PaymentService初期化成功（SDK無し）"}
            else:
                service = PaymentService()
                
                # プラン情報の確認
                plans = service.get_all_plans()
                plan_names = list(plans.keys())
                
                return {
                    "success": True,
                    "message": "PaymentService初期化成功",
                    "details": {
                        "available_plans": plan_names,
                        "total_plans": len(plans)
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"PaymentService初期化エラー: {str(e)}"}
    
    def test_customer_creation(self) -> Dict[str, Any]:
        """顧客作成テスト（モック使用）"""
        if not self.stripe_available:
            return {"success": False, "message": "Stripe SDKが必要"}
        
        try:
            import stripe
            
            # モックオブジェクトを作成
            mock_customer = Mock()
            mock_customer.id = "cus_test123456789"
            mock_customer.email = "test@example.com"
            mock_customer.name = "Test Customer"
            
            with patch('stripe.Customer.create', return_value=mock_customer):
                service = PaymentService()
                
                company_info = {
                    "company_id": "test-company",
                    "name": "テスト会社",
                    "email": "test@example.com"
                }
                
                customer = service.create_customer(company_info)
                
                return {
                    "success": True,
                    "message": "顧客作成テスト成功",
                    "details": {
                        "customer_id": customer.id,
                        "customer_email": customer.email
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"顧客作成テストエラー: {str(e)}"}
    
    def test_payment_method_creation(self) -> Dict[str, Any]:
        """PaymentMethod作成テスト（モック使用）"""
        if not self.stripe_available:
            return {"success": False, "message": "Stripe SDKが必要"}
        
        try:
            import stripe
            
            # テスト用のカード情報（Stripeのテストカード）
            test_card_data = {
                "number": "4242424242424242",  # Visa test card
                "exp_month": 12,
                "exp_year": 2025,
                "cvc": "123",
                "cardholder_name": "Test User"
            }
            
            # モックオブジェクトを作成
            mock_payment_method = Mock()
            mock_payment_method.id = "pm_test123456789"
            mock_payment_method.type = "card"
            mock_payment_method.card.brand = "visa"
            mock_payment_method.card.last4 = "4242"
            
            with patch('stripe.PaymentMethod.create', return_value=mock_payment_method):
                service = PaymentService()
                payment_method = service.create_payment_method(test_card_data)
                
                return {
                    "success": True,
                    "message": "PaymentMethod作成テスト成功",
                    "details": {
                        "payment_method_id": payment_method.id,
                        "card_brand": payment_method.card.brand,
                        "card_last4": payment_method.card.last4
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"PaymentMethod作成テストエラー: {str(e)}"}
    
    def test_price_creation(self) -> Dict[str, Any]:
        """価格作成テスト（モック使用）"""
        if not self.stripe_available:
            return {"success": False, "message": "Stripe SDKが必要"}
        
        try:
            import stripe
            
            # モックオブジェクトを作成
            mock_price = Mock()
            mock_price.id = "price_test123456789"
            mock_price.unit_amount = 198000  # 1980円をcent単位
            mock_price.currency = "jpy"
            mock_price.recurring.interval = "month"
            
            with patch('stripe.Price.create', return_value=mock_price):
                service = PaymentService()
                price = service.create_price("標準", 1980)
                
                return {
                    "success": True,
                    "message": "価格作成テスト成功",
                    "details": {
                        "price_id": price.id,
                        "amount": price.unit_amount,
                        "currency": price.currency
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"価格作成テストエラー: {str(e)}"}
    
    def test_subscription_creation(self) -> Dict[str, Any]:
        """サブスクリプション作成テスト（モック使用）"""
        if not self.stripe_available:
            return {"success": False, "message": "Stripe SDKが必要"}
        
        try:
            import stripe
            
            # モックオブジェクトを作成
            mock_subscription = Mock()
            mock_subscription.id = "sub_test123456789"
            mock_subscription.status = "active"
            mock_subscription.customer = "cus_test123456789"
            mock_subscription.items.data = [Mock()]
            mock_subscription.items.data[0].price.id = "price_test123456789"
            
            with patch('stripe.Subscription.create', return_value=mock_subscription):
                service = PaymentService()
                subscription = service.create_subscription("cus_test123456789", "price_test123456789")
                
                return {
                    "success": True,
                    "message": "サブスクリプション作成テスト成功",
                    "details": {
                        "subscription_id": subscription.id,
                        "status": subscription.status,
                        "customer": subscription.customer
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"サブスクリプション作成テストエラー: {str(e)}"}
    
    def test_subscription_update(self) -> Dict[str, Any]:
        """サブスクリプション更新テスト（モック使用）"""
        if not self.stripe_available:
            return {"success": False, "message": "Stripe SDKが必要"}
        
        try:
            import stripe
            
            # モックオブジェクトを作成
            mock_subscription = Mock()
            mock_subscription.id = "sub_test123456789"
            mock_subscription.items.data = [Mock()]
            mock_subscription.items.data[0].id = "si_test123456789"
            
            mock_updated_subscription = Mock()
            mock_updated_subscription.id = "sub_test123456789"
            mock_updated_subscription.status = "active"
            
            with patch('stripe.Subscription.retrieve', return_value=mock_subscription), \
                 patch('stripe.Subscription.modify', return_value=mock_updated_subscription):
                service = PaymentService()
                subscription = service.update_subscription("sub_test123456789", "price_new123456789")
                
                return {
                    "success": True,
                    "message": "サブスクリプション更新テスト成功",
                    "details": {
                        "subscription_id": subscription.id,
                        "status": subscription.status
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"サブスクリプション更新テストエラー: {str(e)}"}
    
    def test_subscription_cancellation(self) -> Dict[str, Any]:
        """サブスクリプションキャンセルテスト（モック使用）"""
        if not self.stripe_available:
            return {"success": False, "message": "Stripe SDKが必要"}
        
        try:
            import stripe
            
            with patch('stripe.Subscription.delete') as mock_delete:
                mock_delete.return_value = True
                
                service = PaymentService()
                service.cancel_subscription("sub_test123456789")
                
                # デリートが呼ばれたことを確認
                mock_delete.assert_called_once_with("sub_test123456789")
                
                return {
                    "success": True,
                    "message": "サブスクリプションキャンセルテスト成功",
                    "details": {
                        "cancelled_subscription": "sub_test123456789"
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"サブスクリプションキャンセルテストエラー: {str(e)}"}
    
    def test_invoice_retrieval(self) -> Dict[str, Any]:
        """請求書取得テスト（モック使用）"""
        if not self.stripe_available:
            return {"success": False, "message": "Stripe SDKが必要"}
        
        try:
            import stripe
            
            # モック請求書を作成
            mock_invoice = Mock()
            mock_invoice.id = "in_test123456789"
            mock_invoice.status = "paid"
            mock_invoice.amount_paid = 198000
            mock_invoice.created = int(datetime.now().timestamp())
            
            mock_invoices = Mock()
            mock_invoices.data = [mock_invoice]
            
            with patch('stripe.Invoice.list', return_value=mock_invoices):
                service = PaymentService()
                invoices = service.get_customer_invoices("cus_test123456789", limit=5)
                
                return {
                    "success": True,
                    "message": "請求書取得テスト成功",
                    "details": {
                        "invoice_count": len(invoices),
                        "first_invoice_id": invoices[0].id if invoices else None,
                        "first_invoice_status": invoices[0].status if invoices else None
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"請求書取得テストエラー: {str(e)}"}
    
    def test_error_handling(self) -> Dict[str, Any]:
        """エラーハンドリングテスト"""
        if not self.stripe_available:
            return {"success": False, "message": "Stripe SDKが必要"}
        
        try:
            import stripe
            
            # カードエラーのテスト
            card_error = stripe.error.CardError("Card declined", "card_declined", "card_error")
            
            with patch('stripe.PaymentMethod.create', side_effect=card_error):
                service = PaymentService()
                
                try:
                    service.create_payment_method({
                        "number": "4000000000000002",  # Declined card
                        "exp_month": 12,
                        "exp_year": 2025,
                        "cvc": "123",
                        "cardholder_name": "Test User"
                    })
                    return {"success": False, "message": "例外が発生すべきでした"}
                except Exception as e:
                    expected_error = "カード情報が正しくありません" in str(e)
                    return {
                        "success": expected_error,
                        "message": f"エラーハンドリング{'成功' if expected_error else '失敗'}: {str(e)}"
                    }
        except Exception as e:
            return {"success": False, "message": f"エラーハンドリングテストエラー: {str(e)}"}
    
    def test_payment_ui_display(self) -> Dict[str, Any]:
        """決済UI表示テスト（モック使用）"""
        try:
            # PaymentUIの初期化テスト
            if not self.stripe_available:
                # Stripe SDKなしでのUIテスト
                return {"success": True, "message": "UI表示テスト成功（SDK無し）"}
            
            # PaymentServiceをモック
            with patch('services.payment_service.PaymentService') as mock_payment_service:
                mock_service_instance = Mock()
                mock_service_instance.get_all_plans.return_value = {
                    "無料": {"name": "無料プラン", "price": 0, "features": ["基本機能"]},
                    "標準": {"name": "標準プラン", "price": 1980, "features": ["全機能"]}
                }
                mock_payment_service.return_value = mock_service_instance
                
                ui = PaymentUI(mock_service_instance)
                
                return {
                    "success": True,
                    "message": "PaymentUI初期化テスト成功",
                    "details": {
                        "ui_initialized": True,
                        "payment_service_connected": True
                    }
                }
        except Exception as e:
            return {"success": False, "message": f"UI表示テストエラー: {str(e)}"}
    
    def _generate_summary(self) -> Dict[str, Any]:
        """テスト結果のサマリーを生成"""
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r.success])
        failed_tests = total_tests - successful_tests
        
        return {
            "timestamp": datetime.now().isoformat(),
            "stripe_sdk_available": self.stripe_available,
            "test_environment_configured": self.test_env_configured,
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "message": r.message,
                    "duration": r.duration,
                    "details": r.details
                }
                for r in self.test_results
            ]
        }
    
    def generate_test_report(self) -> str:
        """テストレポートを生成"""
        summary = self._generate_summary()
        
        report = f"""
# Stripe決済テストレポート

**実行日時**: {summary['timestamp']}
**Stripe SDK**: {'✅ 利用可能' if summary['stripe_sdk_available'] else '❌ 利用不可'}
**テスト環境設定**: {'✅ 設定済み' if summary['test_environment_configured'] else '⚠️ 未設定'}

## 概要
- **総テスト数**: {summary['summary']['total_tests']}
- **成功**: {summary['summary']['successful_tests']}
- **失敗**: {summary['summary']['failed_tests']}
- **成功率**: {summary['summary']['success_rate']:.1f}%

## テスト結果詳細
"""
        
        for result in summary['test_results']:
            status = "✅" if result['success'] else "❌"
            report += f"\n### {status} {result['test_name']}\n"
            report += f"**結果**: {result['message']}\n"
            report += f"**実行時間**: {result['duration']:.3f}秒\n"
            
            if result.get('details'):
                report += f"**詳細**: {json.dumps(result['details'], indent=2, ensure_ascii=False)}\n"
        
        # 推奨事項
        report += "\n## 推奨事項\n"
        
        if not summary['stripe_sdk_available']:
            report += "1. **Stripe SDKのインストール**: `pip install stripe`\n"
        
        if not summary['test_environment_configured']:
            report += "2. **テスト環境の設定**: STRIPE_SECRET_KEY と STRIPE_PUBLISHABLE_KEY をテスト用キーに設定\n"
        
        if summary['summary']['failed_tests'] > 0:
            report += "3. **失敗したテストの確認**: 上記の詳細結果を参照して問題を修正\n"
        
        return report
    
    def save_results(self, filename: str = None) -> str:
        """テスト結果をファイルに保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stripe_test_results_{timestamp}.json"
        
        filepath = os.path.join(UnifiedConfig.LOGS_DIR, filename)
        
        # JSON結果の保存
        summary = self._generate_summary()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # レポートの保存
        report_filename = filename.replace('.json', '_report.md')
        report_filepath = os.path.join(UnifiedConfig.LOGS_DIR, report_filename)
        
        with open(report_filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_test_report())
        
        print(f"\n💾 テスト結果を保存:")
        print(f"   JSON: {filepath}")
        print(f"   レポート: {report_filepath}")
        
        return filepath


def main():
    """メイン実行関数"""
    print("🚀 Stripe決済テストツール")
    print("=" * 50)
    
    tester = StripePaymentTester()
    results = tester.run_all_tests()
    
    print("\n" + "=" * 50)
    print("📊 テスト結果サマリー")
    print("=" * 50)
    
    print(f"総テスト数: {results['summary']['total_tests']}")
    print(f"成功: {results['summary']['successful_tests']}")
    print(f"失敗: {results['summary']['failed_tests']}")
    print(f"成功率: {results['summary']['success_rate']:.1f}%")
    
    # 結果の保存
    filepath = tester.save_results()
    
    print(f"\n🎉 Stripe決済テスト完了!")
    
    return results


if __name__ == "__main__":
    main()