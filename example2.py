from chatgraph import UserState
from dotenv import load_dotenv
if __name__ == '__main__':
    load_dotenv()

    myUser = UserState(
        customer_id='5565981027703',
        menu='prev-fraudes',
        route='start',
        obs={},
        direction_in=False,
        platform='workplace',
    )
    
    myUser.insert()
    
    myUser = UserState.get_user_state('5565981027703')
    
    print(myUser)
    
    
    myUser.menu = 'state2'
    myUser.update()
    
    myUser.obs = {'obs2': 'obs2'}
    myUser.update()
    
    myUser.delete()