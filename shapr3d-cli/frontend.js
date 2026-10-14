extensions.set('visible-status',async(req,o)=>onUI(()=>({state:inspect(o),pageType:frontendPageType(),normalFrontendTokenCaptured:!projectToken.isNull()})));
