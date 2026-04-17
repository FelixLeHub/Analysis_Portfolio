def _set_home_action(env):
    action = env.ref('freight_forwarding_home.action_freight_forwarding_home_dashboard')
    users = env['res.users'].search([('share', '=', False)])
    users.write({'action_id': action.id})
