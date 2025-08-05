"""
決済管理サービス
Stripe APIを使用した決済機能を提供
"""

import streamlit as st
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Stripe SDK（オプション）
try:
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    HAS_STRIPE_SDK = True
except ImportError:
    print("Stripe SDKがインストールされていません。決済機能は無効化されます。")
    # ダミークラスを作成
    class stripe:
        class PaymentMethod:
            pass
        class Customer:
            pass
        class Price:
            pass
        class Subscription:
            pass
        class Invoice:
            pass
        class error:
            class CardError(Exception):
                pass
    HAS_STRIPE_SDK = False

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentService:
    """決済サービスクラス"""
    
    def _check_stripe_available(self):
        """Stripe SDK利用可能性チェック"""
        if not HAS_STRIPE_SDK:
            raise ImportError("Stripe SDKが利用できません。決済機能を使用するには 'pip install stripe' を実行してください。")
    
    # プラン定義
    PLANS = {
        "無料": {
            "name": "無料プラン",
            "price": 0,
            "features": ["基本的なFAQ機能", "月間質問数: 100件まで"]
        },
        "標準": {
            "name": "標準プラン", 
            "price": 1980,
            "features": ["全FAQ機能", "月間質問数: 1,000件まで", "LINE通知機能"]
        },
        "PRO": {
            "name": "PROプラン",
            "price": 3980,
            "features": ["全機能無制限", "月間質問数: 無制限", "LINE通知機能", "優先サポート"]
        }
    }
    
    def __init__(self):
        self.stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if not self.stripe_key:
            raise ValueError("STRIPE_SECRET_KEY環境変数が設定されていません")
    
    def get_plan_info(self, plan_name: str) -> Dict[str, Any]:
        """プラン情報を取得"""
        return self.PLANS.get(plan_name, {"name": "不明", "price": 0, "features": []})
    
    def get_all_plans(self) -> Dict[str, Dict[str, Any]]:
        """全プラン情報を取得"""
        return self.PLANS
    
    def create_payment_method(self, card_data: Dict[str, Any]) -> stripe.PaymentMethod:
        """PaymentMethodを作成"""
        try:
            payment_method = stripe.PaymentMethod.create(
                type="card",
                card={
                    "number": card_data["number"].replace(" ", ""),
                    "exp_month": card_data["exp_month"],
                    "exp_year": card_data["exp_year"],
                    "cvc": card_data["cvc"],
                },
                billing_details={
                    "name": card_data["cardholder_name"],
                }
            )
            
            logger.info(f"PaymentMethod created: {payment_method.id}")
            return payment_method
            
        except stripe.error.CardError as e:
            logger.error(f"Card error: {e.user_message}")
            raise Exception(f"カード情報が正しくありません: {e.user_message}")
        except Exception as e:
            logger.error(f"PaymentMethod creation failed: {e}")
            raise Exception(f"決済方法の作成に失敗しました: {e}")
    
    def attach_payment_method(self, payment_method_id: str, customer_id: str) -> None:
        """PaymentMethodを顧客に関連付け"""
        try:
            stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
            logger.info(f"PaymentMethod {payment_method_id} attached to customer {customer_id}")
        except Exception as e:
            logger.error(f"PaymentMethod attachment failed: {e}")
            raise Exception(f"決済方法の関連付けに失敗しました: {e}")
    
    def detach_payment_method(self, payment_method_id: str) -> None:
        """PaymentMethodを削除"""
        try:
            stripe.PaymentMethod.detach(payment_method_id)
            logger.info(f"PaymentMethod {payment_method_id} detached")
        except Exception as e:
            logger.error(f"PaymentMethod detachment failed: {e}")
            raise Exception(f"決済方法の削除に失敗しました: {e}")
    
    def create_customer(self, company_info: Dict[str, Any]) -> stripe.Customer:
        """Stripe顧客を作成"""
        try:
            customer = stripe.Customer.create(
                email=company_info.get("email"),
                name=company_info.get("name"),
                metadata={"company_id": company_info.get("company_id")}
            )
            
            logger.info(f"Customer created: {customer.id}")
            return customer
            
        except Exception as e:
            logger.error(f"Customer creation failed: {e}")
            raise Exception(f"顧客の作成に失敗しました: {e}")
    
    def create_price(self, plan_name: str, amount: int) -> stripe.Price:
        """Stripe価格を作成"""
        try:
            price = stripe.Price.create(
                unit_amount=amount * 100,  # 円をcent単位に変換
                currency='jpy',
                recurring={'interval': 'month'},
                product_data={'name': f'{plan_name}プラン'},
            )
            
            logger.info(f"Price created: {price.id} for plan {plan_name}")
            return price
            
        except Exception as e:
            logger.error(f"Price creation failed: {e}")
            raise Exception(f"価格の作成に失敗しました: {e}")
    
    def create_subscription(self, customer_id: str, price_id: str) -> stripe.Subscription:
        """サブスクリプションを作成"""
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
            )
            
            logger.info(f"Subscription created: {subscription.id}")
            return subscription
            
        except Exception as e:
            logger.error(f"Subscription creation failed: {e}")
            raise Exception(f"サブスクリプションの作成に失敗しました: {e}")
    
    def update_subscription(self, subscription_id: str, new_price_id: str) -> stripe.Subscription:
        """サブスクリプションを更新"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            updated_subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription.items.data[0].id,
                    'price': new_price_id,
                }]
            )
            
            logger.info(f"Subscription updated: {subscription_id}")
            return updated_subscription
            
        except Exception as e:
            logger.error(f"Subscription update failed: {e}")
            raise Exception(f"サブスクリプションの更新に失敗しました: {e}")
    
    def cancel_subscription(self, subscription_id: str) -> None:
        """サブスクリプションをキャンセル"""
        try:
            stripe.Subscription.delete(subscription_id)
            logger.info(f"Subscription cancelled: {subscription_id}")
        except Exception as e:
            logger.error(f"Subscription cancellation failed: {e}")
            raise Exception(f"サブスクリプションのキャンセルに失敗しました: {e}")
    
    def get_customer_payment_methods(self, customer_id: str) -> List[stripe.PaymentMethod]:
        """顧客の決済方法一覧を取得"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            return payment_methods.data
        except Exception as e:
            logger.error(f"Failed to get payment methods: {e}")
            return []
    
    def get_subscription_info(self, subscription_id: str) -> Optional[stripe.Subscription]:
        """サブスクリプション情報を取得"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except Exception as e:
            logger.error(f"Failed to get subscription info: {e}")
            return None
    
    def get_customer_invoices(self, customer_id: str, limit: int = 10) -> List[stripe.Invoice]:
        """顧客の請求書一覧を取得"""
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit
            )
            return invoices.data
        except Exception as e:
            logger.error(f"Failed to get invoices: {e}")
            return []


class PaymentUI:
    """決済UI関連のクラス"""
    
    def __init__(self, payment_service: PaymentService):
        self.payment_service = payment_service
    
    def display_current_plan(self, company_id: str) -> None:
        """現在のプラン表示"""
        current_plan = self.get_current_plan(company_id)
        plan_info = self.payment_service.get_plan_info(current_plan)
        
        st.subheader("現在のプラン")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("プラン名", plan_info["name"])
        with col2:
            st.metric("月額料金", f"¥{plan_info['price']:,}")
        with col3:
            next_billing = self.get_next_billing_date(company_id)
            st.metric("次回請求日", next_billing.strftime("%Y/%m/%d") if next_billing else "なし")
    
    def display_payment_history(self, company_id: str) -> None:
        """決済履歴表示"""
        st.subheader("決済履歴")
        
        customer_id = self.get_stripe_customer_id(company_id)
        if not customer_id:
            st.info("決済履歴がありません")
            return
        
        invoices = self.payment_service.get_customer_invoices(customer_id)
        
        if invoices:
            for invoice in invoices:
                status_icon = "✅" if invoice.status == "paid" else "⏳"
                date_str = datetime.fromtimestamp(invoice.created).strftime("%Y/%m/%d")
                
                with st.expander(f"{date_str} - ¥{invoice.amount_paid // 100:,} ({status_icon})"):
                    st.write(f"ステータス: {invoice.status}")
                    st.write(f"請求書番号: {invoice.number}")
                    if invoice.hosted_invoice_url:
                        st.markdown(f"[請求書を表示]({invoice.hosted_invoice_url})")
        else:
            st.info("決済履歴がありません")
    
    def display_plan_selection(self, company_id: str) -> None:
        """プラン選択表示"""
        st.subheader("プラン変更")
        
        current_plan = self.get_current_plan(company_id)
        plans = self.payment_service.get_all_plans()
        
        col1, col2, col3 = st.columns(3)
        
        for i, (plan_name, plan_data) in enumerate(plans.items()):
            with [col1, col2, col3][i]:
                is_current = current_plan == plan_name
                
                if is_current:
                    st.success(f"🌟 {plan_name} (現在のプラン)")
                else:
                    st.info(f"📋 {plan_name}")
                
                st.write(f"**¥{plan_data['price']:,}/月**")
                
                st.write("**機能:**")
                for feature in plan_data["features"]:
                    st.write(f"• {feature}")
                
                if not is_current:
                    if st.button(f"{plan_name}プランに変更", key=f"change_to_{plan_name}"):
                        self.change_plan(company_id, plan_name, plan_data["price"])
    
    def display_payment_methods(self, company_id: str) -> None:
        """決済方法表示"""
        st.subheader("決済方法管理")
        
        customer_id = self.get_stripe_customer_id(company_id)
        if not customer_id:
            st.info("決済方法が登録されていません")
        else:
            payment_methods = self.payment_service.get_customer_payment_methods(customer_id)
            
            if payment_methods:
                st.write("**登録済みの決済方法:**")
                for method in payment_methods:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        brand = method.card.brand.upper()
                        last4 = method.card.last4
                        exp_month = method.card.exp_month
                        exp_year = method.card.exp_year
                        
                        st.write(f"💳 **** **** **** {last4} ({brand})")
                        st.write(f"有効期限: {exp_month:02d}/{exp_year}")
                    with col2:
                        if st.button("削除", key=f"delete_{method.id}"):
                            self.delete_payment_method(company_id, method.id)
            else:
                st.info("決済方法が登録されていません")
        
        if st.button("新しい決済方法を追加"):
            st.session_state.add_payment_method = True
        
        if st.session_state.get("add_payment_method", False):
            self.display_add_payment_method_form(company_id)
    
    def display_add_payment_method_form(self, company_id: str) -> None:
        """決済方法追加フォーム表示"""
        st.subheader("決済方法の追加")
        
        with st.form("payment_method_form"):
            st.write("**クレジットカード情報**")
            
            card_number = st.text_input("カード番号", placeholder="1234 5678 9012 3456")
            
            col1, col2 = st.columns(2)
            with col1:
                exp_month = st.selectbox("有効期限（月）", range(1, 13))
            with col2:
                exp_year = st.selectbox("有効期限（年）", 
                                      range(datetime.now().year, datetime.now().year + 10))
            
            cvc = st.text_input("CVC", placeholder="123")
            cardholder_name = st.text_input("カード名義人", placeholder="TARO YAMADA")
            
            submit_button = st.form_submit_button("決済方法を追加")
            
            if submit_button:
                if not all([card_number, exp_month, exp_year, cvc, cardholder_name]):
                    st.error("すべての項目を入力してください")
                    return
                
                self.add_payment_method(company_id, {
                    "number": card_number,
                    "exp_month": exp_month,
                    "exp_year": exp_year,
                    "cvc": cvc,
                    "cardholder_name": cardholder_name
                })
    
    def change_plan(self, company_id: str, plan_name: str, price: int) -> None:
        """プラン変更処理"""
        try:
            if plan_name == "無料":
                self.cancel_subscription_for_company(company_id)
                self.update_company_plan(company_id, plan_name)
                st.success("無料プランに変更しました")
            else:
                customer_id = self.get_stripe_customer_id(company_id)
                if not customer_id:
                    st.error("決済方法が登録されていません。先に決済方法を追加してください。")
                    return
                
                payment_methods = self.payment_service.get_customer_payment_methods(customer_id)
                if not payment_methods:
                    st.error("決済方法が登録されていません。先に決済方法を追加してください。")
                    return
                
                success = self.create_or_update_subscription(company_id, plan_name, price)
                
                if success:
                    self.update_company_plan(company_id, plan_name)
                    st.success(f"{plan_name}プランに変更しました")
                else:
                    st.error("プラン変更に失敗しました")
                    
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
        
        st.rerun()
    
    def add_payment_method(self, company_id: str, card_data: Dict[str, Any]) -> None:
        """決済方法追加処理"""
        try:
            # PaymentMethodを作成
            payment_method = self.payment_service.create_payment_method(card_data)
            
            # 顧客を取得または作成
            customer_id = self.get_or_create_stripe_customer(company_id)
            
            # PaymentMethodを顧客に関連付け
            self.payment_service.attach_payment_method(payment_method.id, customer_id)
            
            # データベースに保存
            self.save_payment_method(company_id, payment_method)
            
            st.success("決済方法を追加しました")
            st.session_state.add_payment_method = False
            st.rerun()
            
        except Exception as e:
            st.error(f"決済方法の追加に失敗しました: {e}")
    
    def delete_payment_method(self, company_id: str, payment_method_id: str) -> None:
        """決済方法削除処理"""
        try:
            self.payment_service.detach_payment_method(payment_method_id)
            self.remove_payment_method_from_db(company_id, payment_method_id)
            st.success("決済方法を削除しました")
            st.rerun()
        except Exception as e:
            st.error(f"決済方法の削除に失敗しました: {e}")
    
    # 以下、データベース関連のメソッド（実装は既存のDB構造に合わせて調整）
    def get_current_plan(self, company_id: str) -> str:
        """現在のプランを取得"""
        # データベースから現在のプランを取得
        # 実装は既存のデータベース構造に合わせて調整
        return "無料"  # デフォルト値
    
    def get_next_billing_date(self, company_id: str) -> Optional[datetime]:
        """次回請求日を取得"""
        # データベースまたはStripeから次回請求日を取得
        return None
    
    def get_stripe_customer_id(self, company_id: str) -> Optional[str]:
        """Stripe顧客IDを取得"""
        # データベースからStripe顧客IDを取得
        return None
    
    def get_or_create_stripe_customer(self, company_id: str) -> str:
        """Stripe顧客を取得または作成"""
        customer_id = self.get_stripe_customer_id(company_id)
        
        if customer_id:
            return customer_id
        
        # 新しい顧客を作成
        company_info = self.get_company_info(company_id)
        customer = self.payment_service.create_customer(company_info)
        
        # 顧客IDを保存
        self.save_stripe_customer_id(company_id, customer.id)
        
        return customer.id
    
    def create_or_update_subscription(self, company_id: str, plan_name: str, price: int) -> bool:
        """サブスクリプションを作成または更新"""
        try:
            customer_id = self.get_or_create_stripe_customer(company_id)
            
            # 価格IDを取得または作成
            price_id = self.get_or_create_price(plan_name, price)
            
            # 既存のサブスクリプションを確認
            existing_subscription_id = self.get_subscription_id(company_id)
            
            if existing_subscription_id:
                # 既存のサブスクリプションを更新
                self.payment_service.update_subscription(existing_subscription_id, price_id)
            else:
                # 新しいサブスクリプションを作成
                subscription = self.payment_service.create_subscription(customer_id, price_id)
                self.save_subscription_id(company_id, subscription.id)
            
            return True
            
        except Exception as e:
            logger.error(f"サブスクリプション処理エラー: {e}")
            return False
    
    def get_or_create_price(self, plan_name: str, price: int) -> str:
        """価格を取得または作成"""
        price_id = self.get_price_id(plan_name)
        
        if price_id:
            return price_id
        
        # 新しい価格を作成
        stripe_price = self.payment_service.create_price(plan_name, price)
        
        # 価格IDを保存
        self.save_price_id(plan_name, stripe_price.id)
        
        return stripe_price.id
    
    def cancel_subscription_for_company(self, company_id: str) -> None:
        """会社のサブスクリプションをキャンセル"""
        subscription_id = self.get_subscription_id(company_id)
        if subscription_id:
            self.payment_service.cancel_subscription(subscription_id)
            self.remove_subscription_id(company_id)
    
    # データベース関連のメソッド（実装が必要）
    def update_company_plan(self, company_id: str, plan_name: str) -> None:
        """会社のプランを更新"""
        pass
    
    def get_subscription_id(self, company_id: str) -> Optional[str]:
        """サブスクリプションIDを取得"""
        pass
    
    def save_subscription_id(self, company_id: str, subscription_id: str) -> None:
        """サブスクリプションIDを保存"""
        pass
    
    def remove_subscription_id(self, company_id: str) -> None:
        """サブスクリプションIDを削除"""
        pass
    
    def save_stripe_customer_id(self, company_id: str, customer_id: str) -> None:
        """Stripe顧客IDを保存"""
        pass
    
    def get_price_id(self, plan_name: str) -> Optional[str]:
        """価格IDを取得"""
        pass
    
    def save_price_id(self, plan_name: str, price_id: str) -> None:
        """価格IDを保存"""
        pass
    
    def get_company_info(self, company_id: str) -> Dict[str, Any]:
        """会社情報を取得"""
        return {
            "company_id": company_id,
            "name": "サンプル会社",
            "email": "admin@example.com"
        }
    
    def save_payment_method(self, company_id: str, payment_method: stripe.PaymentMethod) -> None:
        """決済方法を保存"""
        pass
    
    def remove_payment_method_from_db(self, company_id: str, payment_method_id: str) -> None:
        """データベースから決済方法を削除"""
        pass


# 便利関数
def get_payment_service() -> PaymentService:
    """PaymentServiceインスタンスを取得"""
    return PaymentService()


def get_payment_ui() -> PaymentUI:
    """PaymentUIインスタンスを取得"""
    payment_service = get_payment_service()
    return PaymentUI(payment_service)


def payment_management_page(company_id: str) -> None:
    """決済管理ページのメイン関数"""
    st.header("💳 決済管理")
    
    try:
        payment_ui = get_payment_ui()
        
        # 現在のプラン表示
        payment_ui.display_current_plan(company_id)
        
        # 決済履歴表示
        payment_ui.display_payment_history(company_id)
        
        st.markdown("---")
        
        # プラン選択表示
        payment_ui.display_plan_selection(company_id)
        
        st.markdown("---")
        
        # 決済方法管理
        payment_ui.display_payment_methods(company_id)
        
    except Exception as e:
        st.error(f"決済管理ページの読み込み中にエラーが発生しました: {e}")
        logger.error(f"Payment management page error: {e}")