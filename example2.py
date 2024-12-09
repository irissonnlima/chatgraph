from chatgraph import UserState
from dotenv import load_dotenv
if __name__ == '__main__':
    load_dotenv()

    myUser = UserState(
        customer_id='teste de cod',
        menu='state',
        route='channel',
        obs={'obs': 'obs'},
        direction_in=False,
        platform='workplace',
    )
    
    myUser.insert()
    
    myUser.menu = 'state2'
    myUser.update()
    
    myUser.obs = {'obs2': 'obs2'}
    myUser.update()
    
    myUser.delete()