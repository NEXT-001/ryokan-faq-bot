#!/usr/bin/env python3
"""
Test script to reproduce translation inconsistency in tourism responses
"""
from services.unified_chat_service import UnifiedChatService

def test_translation_inconsistency():
    """Test the same Korean query multiple times to show inconsistent translation behavior"""
    
    chat_service = UnifiedChatService()
    
    # Same Korean query: "추천 관광지는?" (What are recommended tourist spots?)
    user_input = "추천 관광지는?"
    
    print("="*80)
    print("TESTING TRANSLATION INCONSISTENCY")
    print("="*80)
    print(f"Korean Query: {user_input}")
    print()
    
    # Test with different locations to simulate the inconsistent behavior
    test_locations = [
        {
            'manual_location': '鎌倉',
            'description': 'Test Case 1 (Kamakura) - Expected CONSISTENT translation'
        },
        {
            'manual_location': '京都', 
            'description': 'Test Case 2 (Kyoto) - Expected INCONSISTENT translation'
        }
    ]
    
    for i, location_context in enumerate(test_locations, 1):
        print(f"\n{'-'*60}")
        print(f"TEST {i}: {location_context['description']}")
        print(f"Location: {location_context['manual_location']}")
        print(f"{'-'*60}")
        
        try:
            response = chat_service.get_unified_response(
                user_input=user_input,
                company_id='demo-company',
                user_info="Test User",
                location_context=location_context
            )
            
            print(f"Response Type: {response.get('response_type', 'unknown')}")
            print(f"Original Language: {response.get('original_language', 'unknown')}")
            print(f"Translated Input: {response.get('translated_input', 'unknown')}")
            print("\nResponse Answer:")
            print(response.get('answer', 'No answer'))
            
            # Analyze translation consistency
            answer = response.get('answer', '')
            has_korean_header = any(korean_word in answer for korean_word in ['관광정보', '정보', '자세한'])
            has_japanese_content = any(japanese_char in answer for japanese_char in ['を', 'に', 'は', 'が', 'です', 'ます'])
            
            print(f"\n📊 ANALYSIS:")
            print(f"  Has Korean Header: {has_korean_header}")
            print(f"  Has Japanese Content: {has_japanese_content}")
            print(f"  Translation Consistent: {not (has_korean_header and has_japanese_content)}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("ROOT CAUSE ANALYSIS:")
    print("="*80)
    print("1. format_google_places_response() generates responses in target language")
    print("2. generate_tourism_response_by_city() may generate mixed-language content") 
    print("3. Response type 'tourism' is excluded from translation in line 155")
    print("4. But some tourism responses contain untranslated Japanese content")
    print("5. This causes partial translation: header in Korean, content in Japanese")

if __name__ == "__main__":
    test_translation_inconsistency()