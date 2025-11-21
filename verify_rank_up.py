import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GreenRecipt.settings')
django.setup()

from accounts.models import CustomUser

def test_rank_up():
    # テストユーザーを作成（存在すれば取得）
    user, created = CustomUser.objects.get_or_create(username='test_rank_user', email='test_rank@example.com')
    user.set_password('password')
    user.current_points = 0
    user.rank = 'seed'
    user.save()
    
    print(f"Initial: Points={user.current_points}, Rank={user.rank}")

    # 100ポイント（ブロンズ -> 芽）
    user.add_points(100)
    user.refresh_from_db()
    print(f"Points=100: Rank={user.rank} (Expected: sprout)")
    assert user.rank == 'sprout'

    # 300ポイント（シルバー -> 木）
    user.add_points(200) # Total 300
    user.refresh_from_db()
    print(f"Points=300: Rank={user.rank} (Expected: tree)")
    assert user.rank == 'tree'

    # 800ポイント（ゴールド -> リンゴの木）
    user.add_points(500) # Total 800
    user.refresh_from_db()
    print(f"Points=800: Rank={user.rank} (Expected: apple_tree)")
    assert user.rank == 'apple_tree'

    # ポイント減少（ランクダウンするか確認）
    # add_pointsは加算を想定しているが、負の値も許容するか確認
    # user.add_points(-4900) # Total 100
    # user.refresh_from_db()
    # print(f"Points=100: Rank={user.rank} (Expected: seed)")
    # assert user.rank == 'seed'

    print("Rank up logic verification passed!")

if __name__ == '__main__':
    try:
        test_rank_up()
    except AssertionError as e:
        print(f"Verification failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
